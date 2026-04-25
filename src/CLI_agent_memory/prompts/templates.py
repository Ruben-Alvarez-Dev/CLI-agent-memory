"""Prompt templates — generated per phase."""

from __future__ import annotations

from CLI_agent_memory.domain.types import ContextPack

# Done detection patterns — matched case-insensitively in LLM output
DONE_SIGNALS = [
    "DONE CODING",
    "ALL STEPS COMPLETE",
    "IMPLEMENTATION COMPLETE",
    "ALL CHANGES APPLIED",
    "TASK COMPLETE",
]


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
        parts.append("## Relevant files\n" + "\n".join(f"- {f}" for f in files[:50]))
    if context.context_text:
        parts.append("## Context\n" + context.context_text[:2000])
    parts.append(
        "## Instructions\n"
        "Implement the next step from the plan. Make minimal changes.\n"
        "To create or edit a file, use one of these formats:\n\n"
        'Format 1 (preferred):\n'
        '**File: path/to/file.ext**\n'
        '```\n'
        'full file content here\n'
        '```\n\n'
        'Format 2 (with language):\n'
        '```python\n'
        '# path: src/module.py\n'
        'content here\n'
        '```\n\n'
        "Format 3 (full rewrite):\n"
        "```\n"
        "FILE: path/to/file.ext\n"
        "content here\n"
        "```\n"
        "```\n\n"
        "CRITICAL: When ALL steps from the plan are implemented and tests "
        "would pass, say EXACTLY one of: DONE CODING, ALL STEPS COMPLETE, "
        "or IMPLEMENTATION COMPLETE.\n"
        "If there are still steps remaining, continue implementing them."
    )
    return "\n\n".join(parts)


def verification_prompt(test_output: str, plan: str, files_changed: list[str] | None = None) -> str:
    parts = [
        "## Tests failed\n\n"
        f"```\n{test_output}\n```\n",
    ]
    if files_changed:
        parts.append("## Files changed in last iteration\n" + "\n".join(f"- {f}" for f in files_changed))
    parts.append(
        "## Plan\n" + plan + "\n\n"
        "## Instructions\n"
        "Analyze the test failures carefully. "
        "Fix ONLY what's broken — make the minimal change needed. "
        "After fixing, say DONE CODING if all tests should now pass."
    )
    return "\n\n".join(parts)


def intervention_prompt(reason: str, recent_context: str = "") -> str:
    prompts = {
        "no_edits": (
            "You have made no file changes for several turns. "
            "Review your approach and try a different strategy. "
            "Focus on one specific file or function at a time."
        ),
        "same_error": (
            "You keep encountering the same error. "
            "Read the error carefully. Try a completely different approach. "
            "Do not retry the same solution."
        ),
    }
    base = prompts.get(reason, f"Stagnation detected: {reason}. Change your approach.")
    if recent_context:
        base += f"\n\n## Recent context (what you've tried)\n{recent_context}"
    return base


def is_done_signal(text: str) -> bool:
    """Check if LLM output signals task completion."""
    upper = text.upper()
    # Check for done signals in the last 200 chars (most likely location)
    tail = upper[-200:] if len(upper) > 200 else upper
    for signal in DONE_SIGNALS:
        if signal in tail:
            return True
    return False
