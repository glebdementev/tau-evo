"""Test the merge pipeline: partition, conflict detection, and LLM resolution."""

from evo.merge.partition import partition_and_detect
from evo.merge.resolver import resolve_conflict
from evo.merge.merge import merge_fixes
from evo.merge.types import ConflictGroup, Region
from evo.models import FixResult, Patch


def _fix(task_id: str, patches: list[Patch], fixed: bool = True) -> FixResult:
    return FixResult(
        task_id=task_id,
        baseline_reward=0.0,
        patched_reward=1.0 if fixed else 0.0,
        diagnosis=f"Fix for {task_id}",
        patches=patches,
        retries=0,
        fixed=fixed,
    )


BASE_PROMPT = (
    "You are a helpful airline agent.\n"
    "Always greet the customer politely.\n"
    "Follow company policy at all times.\n"
    "Never reveal internal system details."
)

TOOL_SCHEMAS = {
    "search_flights": {
        "name": "search_flights",
        "description": "Search for available flights",
        "parameters": {"type": "object", "properties": {"origin": {"type": "string"}}},
    },
    "book_flight": {
        "name": "book_flight",
        "description": "Book a flight for the customer",
        "parameters": {"type": "object", "properties": {"flight_id": {"type": "string"}}},
    },
}


# ── Unit tests (no LLM) ──────────────────────────────────────────────────

def test_no_conflict_different_targets():
    """Patches to different tools never conflict."""
    fixes = [
        _fix("t1", [Patch(old_text="Search for available flights", new_text="Search for flights by route", tool_name="search_flights")]),
        _fix("t2", [Patch(old_text="Book a flight for the customer", new_text="Book and confirm a flight", tool_name="book_flight")]),
    ]
    clean, conflicts = partition_and_detect(fixes, BASE_PROMPT, TOOL_SCHEMAS, {})
    assert len(clean) == 2
    assert len(conflicts) == 0


def test_no_conflict_disjoint_prompt_regions():
    """Prompt patches touching different regions don't conflict."""
    fixes = [
        _fix("t1", [Patch(old_text="Always greet the customer politely.", new_text="Always greet the customer warmly and politely.")]),
        _fix("t2", [Patch(old_text="Never reveal internal system details.", new_text="Never reveal internal system details or pricing logic.")]),
    ]
    clean, conflicts = partition_and_detect(fixes, BASE_PROMPT, TOOL_SCHEMAS, {})
    assert len(clean) == 2
    assert len(conflicts) == 0


def test_conflict_overlapping_prompt_regions():
    """Prompt patches touching the same region produce a conflict group."""
    fixes = [
        _fix("t1", [Patch(old_text="Always greet the customer politely.", new_text="Always greet the customer warmly.")]),
        _fix("t2", [Patch(old_text="Always greet the customer politely.", new_text="Always greet the customer formally.")]),
    ]
    clean, conflicts = partition_and_detect(fixes, BASE_PROMPT, TOOL_SCHEMAS, {})
    assert len(clean) == 0
    assert len(conflicts) == 1
    assert set(conflicts[0].task_ids) == {"t1", "t2"}


def test_appends_never_conflict():
    """Append patches (old_text='') are always clean."""
    fixes = [
        _fix("t1", [Patch(old_text="", new_text="Rule: always confirm booking details.")]),
        _fix("t2", [Patch(old_text="", new_text="Rule: check customer loyalty status.")]),
    ]
    clean, conflicts = partition_and_detect(fixes, BASE_PROMPT, TOOL_SCHEMAS, {})
    assert len(clean) == 2
    assert len(conflicts) == 0


def test_mixed_clean_and_conflict():
    """Mix of conflicting prompt patches and clean tool patches."""
    fixes = [
        _fix("t1", [
            Patch(old_text="Always greet the customer politely.", new_text="Greet warmly."),
            Patch(old_text="Search for available flights", new_text="Search flights by date", tool_name="search_flights"),
        ]),
        _fix("t2", [
            Patch(old_text="Always greet the customer politely.", new_text="Greet formally."),
            Patch(old_text="Book a flight for the customer", new_text="Book flight", tool_name="book_flight"),
        ]),
    ]
    clean, conflicts = partition_and_detect(fixes, BASE_PROMPT, TOOL_SCHEMAS, {})
    assert len(clean) == 2  # two tool patches
    assert len(conflicts) == 1  # one prompt conflict group


def test_unfixed_patches_ignored():
    """Only fixed=True patches are considered by merge_fixes (no LLM call)."""
    fixes = [
        _fix("t1", [Patch(old_text="Always greet the customer politely.", new_text="Greet warmly.")], fixed=True),
        _fix("t2", [Patch(old_text="Always greet the customer politely.", new_text="Greet formally.")], fixed=False),
    ]
    # Since only one fix is "fixed", there should be no conflict.
    clean, conflicts = partition_and_detect(
        [f for f in fixes if f.fixed], BASE_PROMPT, TOOL_SCHEMAS, {},
    )
    assert len(clean) == 1
    assert len(conflicts) == 0


# ── Live LLM test (calls kimi-k2.5 via OpenRouter) ───────────────────────

def test_llm_resolver_live():
    """Actually call the LLM merger to resolve a conflict. Requires OPENROUTER_API_KEY."""
    import os
    if not os.environ.get("OPENROUTER_API_KEY"):
        import pytest
        pytest.skip("OPENROUTER_API_KEY not set")

    fix1 = _fix("t1", [Patch(old_text="Always greet the customer politely.", new_text="Always greet the customer warmly and ask how you can help.")])
    fix2 = _fix("t2", [Patch(old_text="Always greet the customer politely.", new_text="Always greet the customer politely and confirm their identity.")])

    group = ConflictGroup(
        target="prompt",
        regions=[
            Region(patch=fix1.patches[0], start=BASE_PROMPT.index("Always greet"), end=BASE_PROMPT.index("Always greet") + len("Always greet the customer politely."), fix=fix1),
            Region(patch=fix2.patches[0], start=BASE_PROMPT.index("Always greet"), end=BASE_PROMPT.index("Always greet") + len("Always greet the customer politely."), fix=fix2),
        ],
        base_text=BASE_PROMPT,
    )

    patch = resolve_conflict(group)
    assert patch is not None, "LLM merger returned None"
    assert patch.old_text in BASE_PROMPT, f"old_text not found in base: {patch.old_text!r}"
    assert patch.new_text != patch.old_text, "new_text same as old_text"
    # The merged text should incorporate both intents (warm greeting + identity confirmation).
    print(f"\nMerged patch:\n  old: {patch.old_text!r}\n  new: {patch.new_text!r}")
