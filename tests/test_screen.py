"""Tests for the tool-reliability screen.

The screen decides which models are admitted to cross-model replication, so a bug
here would silently admit a model that cannot chain (inflating a generalization
claim) or reject one that can. The judging logic is tested against a FakeBackend so
no model is needed.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "screen_models", Path(__file__).resolve().parents[1] / "paper-recovery" / "screen_models.py"
)
screen_models = importlib.util.module_from_spec(_spec)
sys.modules["screen_models"] = screen_models
_spec.loader.exec_module(screen_models)

PASS_THRESHOLD = screen_models.PASS_THRESHOLD
SCREEN_TASKS = screen_models.SCREEN_TASKS
_matches = screen_models._matches
_tokens = screen_models._tokens


class TestTokenMatching:
    def test_whole_token_not_substring(self) -> None:
        """12 must not match inside 120 -- the study's standing numeric rule."""
        assert not _matches("the answer is 120", 12)
        assert _matches("the answer is 12", 12)

    def test_integer_valued_float_matches_plain_digits(self) -> None:
        assert _matches("result: 126", 126.0)

    def test_matches_within_punctuation(self) -> None:
        assert _matches("The final number is 126.", 126.0)
        assert _matches("(126)", 126.0)

    def test_absent_value(self) -> None:
        assert not _matches("no numbers here", 42)

    def test_tokens_splits_on_non_numeric(self) -> None:
        assert _tokens("a1 b22 c3.5") == {"1", "22", "3.5"}


class TestTaskDefinitions:
    def test_every_task_is_genuinely_two_step(self) -> None:
        """The answer must not be reachable without the intermediate value."""
        for t in SCREEN_TASKS:
            assert t.first != t.answer

    def test_intermediate_is_not_in_the_prompt(self) -> None:
        """If the first result appears in the prompt, 'threading' is unfalsifiable:
        the model could echo it without ever using the tool's return."""
        for t in SCREEN_TASKS:
            assert not _matches(t.prompt, t.first), f"{t.prompt!r} leaks its intermediate"

    def test_arithmetic_is_correct(self) -> None:
        """Guards against a typo making a task unpassable and a model wrongly rejected."""
        expected = [(42.0, 126.0), (22.0, 110.0), (42.0, 61.0),
                    (48.0, 81.0), (100.0, 200.0), (81.0, 100.0)]
        assert [(t.first, t.answer) for t in SCREEN_TASKS] == expected

    def test_threshold_requires_all_tasks(self) -> None:
        assert PASS_THRESHOLD == len(SCREEN_TASKS)


class _Step:
    def __init__(self, tool_name=None, tool_args=None):
        self.tool_name = tool_name
        self.tool_args = tool_args or {}


class _Result:
    def __init__(self, steps, final_output):
        self.steps = steps
        self.final_output = final_output
        self.stopped_reason = "final"


def _judge(monkeypatch, steps, final_output):
    """Run screen_task with a stubbed agent producing the given behaviour."""
    monkeypatch.setattr(screen_models, "run_agent",
                        lambda **kw: _Result(steps, final_output))
    monkeypatch.setattr(screen_models, "OllamaBackend", lambda *a, **k: object())
    return screen_models.screen_task(SCREEN_TASKS[0], object(), screen_models.Config())


class TestJudging:
    """SCREEN_TASKS[0]: add 17+25 -> 42, then x3 -> 126."""

    def test_clean_chain_passes(self, monkeypatch) -> None:
        steps = [_Step("add", {"a": 17, "b": 25}), _Step("multiply", {"a": 42, "b": 3})]
        out = _judge(monkeypatch, steps, "The final number is 126.")
        assert out.clean and out.threaded and out.correct_answer

    def test_correct_answer_without_threading_is_NOT_clean(self, monkeypatch) -> None:
        """A model that reasons in text cannot be repaired by a tool-based
        intervention, so a right answer alone must not admit it."""
        out = _judge(monkeypatch, [], "17+25 is 42, times 3 is 126.")
        assert out.correct_answer
        assert not out.clean
        assert "no tool call" in out.note

    def test_literal_result_string_fails(self, monkeypatch) -> None:
        """The characteristic llama3.1 failure: passing 'result' instead of the number."""
        steps = [_Step("add", {"a": 17, "b": 25}),
                 _Step("multiply", {"a": "result", "b": 3})]
        out = _judge(monkeypatch, steps, "The final number is 126.")
        assert not out.clean
        assert "thread" in out.note

    def test_single_call_fails(self, monkeypatch) -> None:
        out = _judge(monkeypatch, [_Step("add", {"a": 17, "b": 25})], "42")
        assert not out.clean
        assert "single tool call" in out.note

    def test_threaded_but_wrong_answer_fails(self, monkeypatch) -> None:
        steps = [_Step("add", {"a": 17, "b": 25}), _Step("multiply", {"a": 42, "b": 3})]
        out = _judge(monkeypatch, steps, "The final number is 999.")
        assert not out.clean
        assert out.threaded and not out.correct_answer
        assert "wrong final answer" in out.note

    def test_threading_detected_in_any_later_call(self, monkeypatch) -> None:
        """Extra exploratory calls before the threading call must not break detection."""
        steps = [_Step("add", {"a": 17, "b": 25}), _Step("add", {"a": 1, "b": 1}),
                 _Step("multiply", {"a": 42, "b": 3})]
        out = _judge(monkeypatch, steps, "126")
        assert out.clean

    def test_first_call_containing_the_value_does_not_count(self, monkeypatch) -> None:
        """Threading means a LATER call consumed the result; the first call cannot."""
        steps = [_Step("multiply", {"a": 42, "b": 3})]
        out = _judge(monkeypatch, steps, "126")
        assert not out.threaded
