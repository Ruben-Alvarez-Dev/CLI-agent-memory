"""LoopEngine — state machine: PLANNING → CODING → VERIFICATION → DONE/FAILED."""
from __future__ import annotations
import logging
import time
from pathlib import Path
from CLI_agent_memory.config import LoopConfig
from CLI_agent_memory.domain.file_ops import detect_git_changes, parse_and_write_files, trim_history
from CLI_agent_memory.domain.protocols import (
    LLMClient, MemoryProtocol, ThinkingProtocol, VaultProtocol, WorkspaceProtocol,
)
from CLI_agent_memory.domain.stagnation import StagnationMonitor
from CLI_agent_memory.domain.state import TaskContext
from CLI_agent_memory.domain.types import AgentState, Message, TaskResult, ContextPack
from CLI_agent_memory.prompts.templates import (
    coding_prompt, intervention_prompt, is_done_signal, planning_prompt, verification_prompt,
)
logger = logging.getLogger(__name__)
MAX_HISTORY = 30


class LoopEngine:
    def __init__(self, llm: LLMClient, memory: MemoryProtocol, thinking: ThinkingProtocol,
                 workspace: WorkspaceProtocol, vault: VaultProtocol, config: LoopConfig):
        self.llm, self.memory, self.thinking = llm, memory, thinking
        self.workspace, self.vault, self.config = workspace, vault, config
        self.stagnation = StagnationMonitor(max_failures=config.max_stagnation)

    async def run(self, task_description: str, repo_path: Path) -> TaskResult:
        t0 = time.time()
        branch = f"agent-memory/{int(t0)}"
        wt = self.workspace.create(branch)
        ctx = self._init_ctx(wt, task_description, branch)
        history = [Message(role="system", content="You are a coding agent.")]
        try:
            await self._execute_loop(ctx, history)
            return TaskResult(
                task_id=ctx.task_id, status=ctx.state, worktree_path=str(wt),
                plan=ctx.plan, tests_passed=(ctx.state == AgentState.DONE),
                duration_seconds=time.time() - t0,
            )
        except Exception as e:
            logger.exception("Loop error")
            ctx.transition(AgentState.FAILED)
            return TaskResult(task_id=ctx.task_id, status=AgentState.FAILED,
                              worktree_path=str(wt), error=str(e), duration_seconds=time.time() - t0)

    async def resume(self, task_id: str, repo_path: Path) -> TaskResult | None:
        wt_base = repo_path / ".worktrees"
        if not wt_base.exists():
            return None
        for wt_dir in wt_base.iterdir():
            if not wt_dir.is_dir():
                continue
            ctx = TaskContext.find_in_worktree(wt_dir)
            if ctx and ctx.task_id == task_id and ctx.state not in (AgentState.DONE, AgentState.FAILED):
                logger.info("Resuming %s from %s (%s)", task_id, wt_dir, ctx.state)
                history = [Message(role="system", content="Resuming task. Continue from where you left off.")]
                await self._execute_loop(ctx, history)
                return TaskResult(task_id=ctx.task_id, status=ctx.state,
                                  worktree_path=str(wt_dir), plan=ctx.plan,
                                  tests_passed=(ctx.state == AgentState.DONE))
        return None

    def get_status(self, repo_path: Path) -> TaskContext | None:
        wt_base = repo_path / ".worktrees"
        if not wt_base.exists():
            return None
        latest = None
        for wt_dir in wt_base.iterdir():
            if not wt_dir.is_dir():
                continue
            ctx = TaskContext.find_in_worktree(wt_dir)
            if ctx and ctx.state not in (AgentState.DONE, AgentState.FAILED):
                if latest is None or ctx.iteration > latest.iteration:
                    latest = ctx
        return latest

    # ── Private phase methods ──

    async def _plan(self, ctx: TaskContext, task: str, history: list[Message]) -> None:
        context = await self.memory.recall(task)
        prompt = planning_prompt(task, context)
        history.append(Message(role="user", content=prompt))
        resp = await self.llm.generate(prompt, history, temperature=0.5)
        history.append(Message(role="assistant", content=resp.text))
        ctx.plan = resp.text
        self.workspace.write_file(ctx.worktree_path, "PLAN.md", ctx.plan)
        await self.vault.write("Decisions", f"plan-{ctx.task_id}", f"# Plan\n\n{ctx.plan}")
        ctx.transition(AgentState.CODING)

    async def _code(self, ctx: TaskContext, history: list[Message]) -> None:
        # Throttle RAG: every iter on first 3, then every 5th
        context = await self.memory.recall(ctx.task_description + "\n" + ctx.plan) \
            if ctx.iteration <= 3 or ctx.iteration % 5 == 0 else ContextPack()
        files = self.workspace.list_files(ctx.worktree_path)
        prompt = coding_prompt(ctx.plan, context, files)
        history.append(Message(role="user", content=prompt))
        resp = await self.llm.generate(prompt, history, temperature=0.1)
        history.append(Message(role="assistant", content=resp.text))

        files_edited = parse_and_write_files(ctx.worktree_path, resp.text)
        if files_edited == 0:
            files_edited = len(detect_git_changes(ctx.worktree_path))

        stag = self.stagnation.record_turn(files_edited=files_edited)
        if stag.is_stagnant:
            recent = "\n".join(f"- {m.content[:120]}" for m in history[-6:] if m.role == "assistant")
            history.append(Message(role="user", content=intervention_prompt(stag.reason, recent)))
            trim_history(history, keep_last=6)
            self.stagnation.reset()

        trim_history(history, keep_last=MAX_HISTORY)
        if is_done_signal(resp.text):
            ctx.transition(AgentState.VERIFICATION)

    async def _verify(self, ctx: TaskContext, history: list[Message]) -> None:
        cmd = self.config.test_command or "echo 'No test command configured'"
        result = self.workspace.run_command(ctx.worktree_path, cmd)
        if result.success:
            await self.memory.store("task_completed", f"Task {ctx.task_id} OK", tags=["task"])
            await self.vault.write("Decisions", f"result-{ctx.task_id}", f"# Result\n\nTests passed.\n\n{ctx.plan}")
            ctx.transition(AgentState.DONE)
        else:
            await self.memory.ingest("test_failure", result.stderr)
            changed = detect_git_changes(ctx.worktree_path)
            history.append(Message(role="user", content=verification_prompt(result.stderr, ctx.plan, changed)))
            stag = self.stagnation.record_turn(files_edited=0, current_error=result.stderr)
            if stag.is_stagnant:
                history.append(Message(role="user", content=intervention_prompt(stag.reason)))
                trim_history(history, keep_last=6)
                self.stagnation.reset()
            ctx.transition(AgentState.CODING)

    def _init_ctx(self, wt: Path, task: str, branch: str) -> TaskContext:
        ctx = TaskContext(wt)
        ctx.task_description = task
        ctx.generate_task_id(branch)
        ctx.transition(AgentState.PLANNING)
        return ctx

    async def _execute_loop(self, ctx: TaskContext, history: list[Message]) -> None:
        while ctx.state not in (AgentState.DONE, AgentState.FAILED):
            if ctx.iteration >= self.config.max_iterations:
                logger.warning("Max iterations (%d)", self.config.max_iterations)
                ctx.transition(AgentState.FAILED); break
            ctx.iteration += 1
            handlers = {AgentState.PLANNING: lambda: self._plan(ctx, ctx.task_description, history),
                       AgentState.CODING: lambda: self._code(ctx, history),
                       AgentState.VERIFICATION: lambda: self._verify(ctx, history)}
            if h := handlers.get(ctx.state): await h()
