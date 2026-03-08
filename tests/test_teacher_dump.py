"""Diagnostic test: dumps everything the teacher sees at each stage.

Run with: pytest tests/test_teacher_dump.py -s
"""

import json
from copy import deepcopy
from types import SimpleNamespace

from pydantic import BaseModel
from tau2.data_model.message import (
    AssistantMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)

from evo.reflection.formatting import (
    format_messages,
    format_preprocessors,
    format_reward,
    format_tools,
)
from evo.reflection.prompts import ESCALATION_PROMPT, REFLECTION_PROMPT, RETRY_PROMPT


# ---------------------------------------------------------------------------
# Fake tau2 objects
# ---------------------------------------------------------------------------

class FakeParams(BaseModel):
    reservation_id: str
    reason: str = "customer_request"

class FakeReturns(BaseModel):
    status: str

class FakeTool:
    name = "cancel_reservation"
    short_desc = "Cancel a reservation"
    long_desc = "Cancel a reservation and process refund if applicable."

    @property
    def params(self):
        return FakeParams

    @property
    def returns(self):
        return FakeReturns

    @property
    def openai_schema(self):
        return {
            "type": "function",
            "function": {
                "name": "cancel_reservation",
                "description": "Cancel a reservation and process refund if applicable.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {"type": "string", "description": "The reservation ID"},
                        "reason": {"type": "string", "description": "Cancellation reason"},
                    },
                    "required": ["reservation_id"],
                },
            },
        }


class FakeLookupTool:
    name = "get_reservation_details"
    short_desc = "Look up a reservation"
    long_desc = "Retrieve full reservation details by ID."

    @property
    def params(self):
        return FakeParams  # reuse for simplicity

    @property
    def returns(self):
        return FakeReturns

    @property
    def openai_schema(self):
        return {
            "type": "function",
            "function": {
                "name": "get_reservation_details",
                "description": "Retrieve full reservation details by ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reservation_id": {"type": "string", "description": "The reservation ID"},
                    },
                    "required": ["reservation_id"],
                },
            },
        }


def _make_reward_info(reward=0.3):
    """Fake reward_info with model_dump_json."""
    class R(BaseModel):
        reward: float
        actions_correct: bool
        response_correct: bool
        details: str

    return R(
        reward=reward,
        actions_correct=False,
        response_correct=True,
        details="Agent used wrong cancellation reason; missed refund calculation step.",
    )


def _make_task():
    class EvalCriteria(BaseModel):
        must_cancel: bool
        must_refund: bool
        max_interactions: int
        notes: str

    task = SimpleNamespace(
        user_scenario="Customer wants to cancel reservation ABC123 and get a refund.",
        evaluation_criteria=EvalCriteria(
            must_cancel=True,
            must_refund=True,
            max_interactions=5,
            notes="Agent must verify identity before cancellation.",
        ),
    )
    return task


def _make_messages():
    return [
        SystemMessage(role="system", content="You are an airline customer service agent. Follow policy."),
        UserMessage(role="user", content="Hi, I need to cancel my reservation ABC123."),
        AssistantMessage(
            role="assistant",
            content=None,
            tool_calls=[
                ToolCall(id="c1", name="get_reservation_details", arguments={"reservation_id": "ABC123"}),
            ],
        ),
        ToolMessage(
            id="c1",
            role="tool",
            content=json.dumps({
                "reservation_id": "ABC123",
                "passenger": "Jane Smith",
                "flight": "DL789",
                "status": "confirmed",
                "price": 450.0,
            }),
        ),
        AssistantMessage(
            role="assistant",
            content="I found your reservation. I'll cancel it now.",
        ),
        AssistantMessage(
            role="assistant",
            content=None,
            tool_calls=[
                ToolCall(id="c2", name="cancel_reservation", arguments={"reservation_id": "ABC123", "reason": "no_show"}),
            ],
        ),
        ToolMessage(id="c2", role="tool", content='{"status": "cancelled"}'),
        AssistantMessage(
            role="assistant",
            content="Done — your reservation has been cancelled.",
        ),
    ]


SYSTEM_PROMPT = """\
You are an airline customer service agent.

RULES:
- Always verify passenger identity before making changes.
- Use the correct cancellation reason (customer_request for voluntary cancellations).
- Calculate refund amounts before confirming cancellation.
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_dump_initial_reflection_prompt():
    """Dump the full initial prompt the teacher receives."""
    tools = [FakeLookupTool(), FakeTool()]
    messages = _make_messages()
    task = _make_task()
    reward_info = _make_reward_info()

    tool_defs = format_tools(tools)
    conv_trace = format_messages(messages)
    task_req = f"User scenario: {task.user_scenario}\n\n{task.evaluation_criteria.model_dump_json(indent=2)}"
    reward_str = format_reward(reward_info)

    full_prompt = REFLECTION_PROMPT.format(
        system_prompt=SYSTEM_PROMPT,
        tool_definitions=tool_defs,
        conversation_trace=conv_trace,
        task_requirements=task_req,
        reward_breakdown=reward_str,
    )

    print("\n" + "=" * 80)
    print("INITIAL REFLECTION PROMPT (what teacher sees as first user message)")
    print("=" * 80)
    print(full_prompt)
    print("=" * 80)
    print(f"Total length: {len(full_prompt)} chars, ~{len(full_prompt) // 4} tokens")
    print("=" * 80)

    # Sanity checks
    assert "cancel_reservation" in full_prompt
    assert "get_reservation_details" in full_prompt
    assert "ABC123" in full_prompt
    assert "no_show" in full_prompt  # the bad reason is visible
    assert "customer_request" in full_prompt  # the correct reason is in the system prompt
    assert "reward" in full_prompt.lower()


def test_dump_retry_prompt():
    """Dump what the teacher sees after a failed validation."""
    messages = _make_messages()
    reward_info = _make_reward_info(0.25)

    tool_schemas = {
        "cancel_reservation": FakeTool().openai_schema,
        "get_reservation_details": FakeLookupTool().openai_schema,
    }
    tool_code = {
        "cancel_reservation": 'def preprocess(kwargs):\n    # normalize reason\n    r = kwargs.get("reason", "")\n    if r == "no_show":\n        kwargs["reason"] = "customer_request"\n    return kwargs\n',
    }

    fake_new_sim = SimpleNamespace(
        messages=messages,
        reward_info=reward_info,
    )

    retry = RETRY_PROMPT.format(
        baseline_reward=0.3,
        patched_reward=0.25,
        new_trace=format_messages(messages),
        new_reward=format_reward(reward_info),
        current_prompt=SYSTEM_PROMPT,
        current_tools=json.dumps(list(tool_schemas.values()), indent=2),
        current_preprocessors=format_preprocessors(tool_code),
    )

    print("\n" + "=" * 80)
    print("RETRY PROMPT (what teacher sees after failed validation)")
    print("=" * 80)
    print(retry)
    print("=" * 80)
    print(f"Total length: {len(retry)} chars")
    print("=" * 80)

    assert "DISCARDED" in retry
    assert "0.30" in retry
    assert "0.25" in retry


def test_dump_escalation_prompt():
    """Dump what teacher sees when escalated to tool code patches."""
    messages = _make_messages()
    reward_info = _make_reward_info(0.2)

    tool_schemas = {
        "cancel_reservation": FakeTool().openai_schema,
        "get_reservation_details": FakeLookupTool().openai_schema,
    }

    fake_new_sim = SimpleNamespace(
        messages=messages,
        reward_info=reward_info,
    )

    escalation = ESCALATION_PROMPT.format(
        baseline_reward=0.3,
        patched_reward=0.2,
        new_trace=format_messages(messages),
        new_reward=format_reward(reward_info),
        current_prompt=SYSTEM_PROMPT,
        current_tools=json.dumps(list(tool_schemas.values()), indent=2),
        current_preprocessors=format_preprocessors({}),
    )

    print("\n" + "=" * 80)
    print("ESCALATION PROMPT (what teacher sees when tool code unlocked)")
    print("=" * 80)
    print(escalation)
    print("=" * 80)
    print(f"Total length: {len(escalation)} chars")
    print("=" * 80)

    assert "patch_tool_code" in escalation
    assert "DISCARDED" in escalation


def test_dump_tool_definitions_format():
    """Show exactly how tool schemas are formatted for the teacher."""
    tools = [FakeLookupTool(), FakeTool()]
    formatted = format_tools(tools)

    print("\n" + "=" * 80)
    print("TOOL DEFINITIONS (format_tools output)")
    print("=" * 80)
    print(formatted)
    print("=" * 80)

    # Verify it's valid JSON
    parsed = json.loads(formatted)
    assert len(parsed) == 2


def test_dump_conversation_trace_format():
    """Show how conversation messages are formatted for the teacher."""
    messages = _make_messages()
    formatted = format_messages(messages)

    print("\n" + "=" * 80)
    print("CONVERSATION TRACE (format_messages output)")
    print("=" * 80)
    print(formatted)
    print("=" * 80)

    # Count message types
    lines = formatted.split("\n")
    user_lines = [l for l in lines if l.startswith("[user]")]
    assistant_lines = [l for l in lines if l.startswith("[assistant]")]
    tool_call_lines = [l for l in lines if "[assistant -> tool_call]" in l]
    tool_result_lines = [l for l in lines if l.startswith("[tool_result:")]

    print(f"\nMessage counts: {len(user_lines)} user, {len(assistant_lines)} assistant, "
          f"{len(tool_call_lines)} tool_calls, {len(tool_result_lines)} tool_results")


def test_dump_reward_format():
    """Show how reward info is formatted."""
    reward_info = _make_reward_info()
    formatted = format_reward(reward_info)

    print("\n" + "=" * 80)
    print("REWARD BREAKDOWN (format_reward output)")
    print("=" * 80)
    print(formatted)
    print("=" * 80)

    parsed = json.loads(formatted)
    assert "reward" in parsed
