"""
Tests for the version-controlled system prompt (app/ai/prompts.py).

These don't call an LLM - they just verify the prompt text actually
contains the behavioral rules the rest of the AI layer relies on the
model following (never guess eligibility, always use the tools, ask
for clarification on ambiguous names, treat simulations as
hypothetical). If one of these phrases is ever accidentally removed
while editing the prompt, this is what catches it.
"""

from app.ai.prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_VERSION


def test_prompt_has_a_version():
    assert SYSTEM_PROMPT_VERSION


def test_prompt_forbids_independent_eligibility_decisions():
    assert "Never independently determine" in SYSTEM_PROMPT


def test_prompt_requires_the_eligibility_tools():
    assert "evaluate_replacement" in SYSTEM_PROMPT
    assert "find_replacement_candidates" in SYSTEM_PROMPT


def test_prompt_requires_the_simulation_tool_and_labels_it_hypothetical():
    assert "simulate_extension" in SYSTEM_PROMPT
    assert "hypothetical" in SYSTEM_PROMPT


def test_prompt_requires_clarification_on_ambiguous_results():
    assert "ambiguous" in SYSTEM_PROMPT
    assert "clarify" in SYSTEM_PROMPT.lower()


def test_prompt_forbids_inventing_records():
    assert "Never invent" in SYSTEM_PROMPT
