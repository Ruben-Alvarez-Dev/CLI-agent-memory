"""LoopEngine — state machine: PLANNING → CODING → VERIFICATION → DONE/FAILED."""

from __future__ import annotations
import re
import time
from pathlib import Path

from CLI_agent_memory.config import LoopConfig
from CLI_agent_memory.domain.protocols import (
    LLMClient, MemoryProtocol, ThinkingProtocol, VaultProtocol, WorkspaceProtocol,
)
from CLI_agent_memory.domain.stagnation import StagnationMonitor
from CLI_agent_memory.domain.state import TaskContext
from CLI_agent_memory.domain.types import AgentState, Message, TaskResult, ContextPack
from CLI_agent_memory.prompts.templates import (
    coding_prompt, intervention_prompt, planning_prompt, verification_prompt,
)


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
        ctx = TaskContext(wt)
        ctx.task_description = task_description
        ctx.generate_task_id(branch)
        ctx.transition(AgentState.PLANNING)
        history: list[Message] = [Message(role="system", content="You are a coding agent.")]
        try:
            while ctx.state not in (AgentState.DONE, AgentState.FAILED):
                if ctx.iteration >= self.config.max_iterations:
                    ctx.transition(AgentState.FAILED)
                    break
                ctx.iteration += 1
                if ctx.state == AgentState.PLANNING:
                    await self._plan(ctx, task_description, history)
                elif ctx.state == AgentState.CODING:
                    await self._code(ctx, history)
                elif ctx.state == AgentState.VERIFICATION:
                    await self._verify(ctx, history)
            return TaskResult(task_id=ctx.task_id, status=ctx.state,
                              worktree_path=str(wt), plan=ctx.plan,
                              tests_passed=(ctx.state == AgentState.DONE),
                              duration_seconds=time.time() - t0)
        except Exception as e:
            ctx.transition(AgentState.FAILED)
            return TaskResult(task_id=ctx.task_id, status=AgentState.FAILED,
                              worktree_path=str(wt), error=str(e),
                              duration_seconds=time.time() - t0)

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
        # Throttle RAG to avoid latency murder (only recall on first iteration of coding phase)
        if ctx.iteration == 2 or ctx.iteration % 5 == 0:
            context = await self.memory.recall(ctx.task_description + "\n" + ctx.plan)
        else:
            context = ContextPack()
        
        files = self.workspace.list_files(ctx.worktree_path)
        prompt = coding_prompt(ctx.plan, context, files)
        history.append(Message(role="user", content=prompt))
        resp = await self.llm.generate(prompt, history, temperature=0.1)
        history.append(Message(role="assistant", content=resp.text))
        
        # ── Parse and write files (Fake Programmer Fix) ──
        file_blocks = re.findall(r"\*\*File:\s*(.*?)\*\*\s*```.*?\n(.*?)```", resp.text, re.DOTALL)
        files_edited = 0
        for file_path, content in file_blocks:
            self.workspace.write_file(ctx.worktree_path, file_path.strip(), content.strip() + "\n")
            files_edited += 1

        stag = self.stagnation.record_turn(files_edited=files_edited)
        if stag.is_stagnant:
            history.append(Message(role="user", content=intervention_prompt(stag.reason)))
            history[:] = [history[0]] + history[-2:]  # Fix amnesia: preserve system prompt
            self.stagnation.reset()
        if "DONE CODING" in resp.text.upper():
            ctx.transition(AgentState.VERIFICATION)

    async def _verify(self, ctx: TaskContext, history: list[Message]) -> None:
        cmd = self.config.test_command or "echo 'No test command configured'"
        result = self.workspace.run_command(ctx.worktree_path, cmd)
        if result.success:
            await self.memory.store("task_completed", f"Task {ctx.task_id} OK", tags=["task"])
            await self.vault.write("Decisions", f"result-{ctx.task_id}",
                                   f"# Result\n\nTests passed.\n\n{ctx.plan}")
            ctx.transition(AgentState.DONE)
        else:
            await self.memory.ingest("test_failure", result.stderr)
            history.append(Message(role="user", content=verification_prompt(result.stderr, ctx.plan)))
            stag = self.stagnation.record_turn(files_edited=0, current_error=result.stderr)
            if stag.is_stagnant:
                history.append(Message(role="user", content=intervention_prompt(stag.reason)))
                history[:] = history[-2:]
                self.stagnation.reset()
            ctx.transition(AgentState.CODING)
