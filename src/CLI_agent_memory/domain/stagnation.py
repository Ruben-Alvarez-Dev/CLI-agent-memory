"""StagnationMonitor — detects when the agent is stuck in a loop."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StagnationResult:
    is_stagnant: bool
    reason: str = ""
    intervention: str = ""


DEFAULT_INTERVENTIONS = {
    "no_edits": (
        "You have made no file changes for several turns. "
        "Review your approach and try a different strategy. "
        "Focus on one specific file or function."
    ),
    "same_error": (
        "You keep encountering the same error. "
        "Read the error carefully. Consider a completely different approach. "
        "Do not retry the same solution."
    ),
}


class StagnationMonitor:
    def __init__(self, max_failures: int = 3, interventions: dict[str, str] | None = None):
        self.max_failures = max_failures
        self.interventions = interventions or DEFAULT_INTERVENTIONS
        self._no_edit_count = 0
        self._last_error = ""
        self._same_error_count = 0

    def record_turn(self, files_edited: int, current_error: str = "") -> StagnationResult:
        if files_edited == 0:
            self._no_edit_count += 1
        else:
            self._no_edit_count = 0

        if current_error and current_error == self._last_error:
            self._same_error_count += 1
        elif current_error:
            self._last_error = current_error
            self._same_error_count = 1

        if self._no_edit_count >= self.max_failures:
            return StagnationResult(
                is_stagnant=True,
                reason="no_edits",
                intervention=self.interventions.get("no_edits", ""),
            )

        if self._same_error_count >= self.max_failures:
            return StagnationResult(
                is_stagnant=True,
                reason="same_error",
                intervention=self.interventions.get("same_error", ""),
            )

        return StagnationResult(is_stagnant=False)

    def reset(self) -> None:
        self._no_edit_count = 0
        self._same_error_count = 0
        self._last_error = ""
