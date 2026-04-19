"""Prompt templates — generated per phase."""

from __future__ import annotations

from CLI_agent_memory.domain.types import ContextPack


def system_prompt(role: str = "coding") -> str:
    return (
        f"You are an autonomous {role} agent. "
        "You work in a git worktree. "
        "Always make minimal, focused changes. "
        "Verify your changes compile and pass tests before marking DONE."
    )


def planning_prompt(task: str, context: ContextPack) -> str:
    parts = [
        "## Task\n" + task,
    ]
    if context.context_text:
        parts.append("## Context\n" + context.context_text)
    parts.append(
        "## Instructions\n"
        "Create a PLAN.md with numbered steps. "
        "Each step should be a concrete, verifiable action. "
        "Output ONLY the plan content, nothing else."
    )
    return "\n\n".join(parts)


def coding_prompt(plan: str, context: ContextPack, files: list[str] | None = None) -> str:
    parts = [
        "## Plan\n" + plan,
    ]
    if files:
        parts.append("## Relevant files\n" + "\n".join(f"- {f}" for f in files[:50])) # Limit to 50 files
    if context.context_text:
        parts.append("## Context\n" + context.context_text[:2000]) # Throttle context bloat
    parts.append(
        "## Instructions\n"
        "Implement the next step from the plan. Make minimal changes.\n"
        "To edit a file, you MUST use the following exact format:\n\n"
        "**File: path/to/file.ext**\n"
        "```\n"
        "full file content here\n"
        "```\n\n"
        "When all steps are done, say 'DONE CODING'."
    )
    return "\n\n".join(parts)


def verification_prompt(test_output: str, plan: str) -> str:
    return (
        "## Tests failed\n\n"
        f"```\n{test_output}\n```\n\n"
        "## Plan\n" + plan + "\n\n"
        "## Instructions\n"
        "Fix the failing tests. Make the minimal change needed."
    )


def intervention_prompt(reason: str) -> str:
    prompts = {
        "no_edits": (
            "You have made no file changes for several turns. "
            "Review your approach and try a different strategy."
        ),
        "same_error": (
            "You keep encountering the same error. "
            "Read the error carefully. Try a completely different approach."
        ),
    }
    return prompts.get(reason, f"Stagnation detected: {reason}. Change your approach.")
