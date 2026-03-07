"""Test that _format_messages preserves everything the student model saw.

Builds a realistic tau2 message sequence, converts it to both:
  1. litellm API format (what the student LLM actually received)
  2. teacher text format (what _format_messages produces)

Then checks that every piece of information in (1) is present in (2).
"""

import json

from tau2.data_model.message import (
    AssistantMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.utils.llm_utils import to_litellm_messages

from evo.reflection.formatting import format_messages as _format_messages


def _make_conversation() -> list:
    """Build a synthetic but realistic tau2 conversation."""
    return [
        SystemMessage(role="system", content="You are a helpful airline agent."),
        UserMessage(role="user", content="I want to cancel my flight ABC123."),
        # Assistant calls a tool
        AssistantMessage(
            role="assistant",
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_001",
                    name="get_reservation_details",
                    arguments={"reservation_id": "ABC123"},
                )
            ],
        ),
        # Tool result (long content to test no-truncation)
        ToolMessage(
            id="call_001",
            role="tool",
            content=json.dumps({
                "reservation_id": "ABC123",
                "passenger": "John Doe",
                "flight": "UA456",
                "date": "2026-04-15",
                "status": "confirmed",
                "fare_class": "economy",
                "price": 350.00,
                "segments": [
                    {"from": "SFO", "to": "ORD", "departure": "08:00", "arrival": "14:00"},
                    {"from": "ORD", "to": "JFK", "departure": "15:30", "arrival": "18:45"},
                ],
                "extras": "A" * 600,  # >500 chars to test old truncation bug
            }),
        ),
        # Assistant sends text AND calls a tool (dual content)
        AssistantMessage(
            role="assistant",
            content="I found your reservation. Let me check the cancellation policy.",
            tool_calls=[
                ToolCall(
                    id="call_002",
                    name="get_cancellation_policy",
                    arguments={"fare_class": "economy", "days_before": 30},
                )
            ],
        ),
        ToolMessage(
            id="call_002",
            role="tool",
            content='{"refund_eligible": true, "fee": 50.00, "refund_amount": 300.00}',
        ),
        # Assistant with multiple tool calls in one turn
        AssistantMessage(
            role="assistant",
            content=None,
            tool_calls=[
                ToolCall(
                    id="call_003",
                    name="cancel_reservation",
                    arguments={"reservation_id": "ABC123", "reason": "customer_request"},
                ),
                ToolCall(
                    id="call_004",
                    name="process_refund",
                    arguments={"reservation_id": "ABC123", "amount": 300.00},
                ),
            ],
        ),
        ToolMessage(id="call_003", role="tool", content='{"status": "cancelled"}'),
        ToolMessage(id="call_004", role="tool", content='{"refund_id": "RF789", "status": "processed"}'),
        # Final assistant message
        AssistantMessage(
            role="assistant",
            content="Your flight has been cancelled and a refund of $300 has been processed.",
        ),
    ]


def test_all_student_info_present_in_teacher_view():
    """Every piece of data the student saw must appear in the teacher's trace."""
    messages = _make_conversation()

    # What the student saw (minus system — teacher gets that separately).
    litellm_msgs = to_litellm_messages(messages)
    student_view = [m for m in litellm_msgs if m["role"] != "system"]

    # What the teacher sees.
    teacher_view = _format_messages(messages)

    # Dump both for easy debugging.
    student_json = json.dumps(student_view, indent=2)
    print("=== STUDENT VIEW (litellm API format) ===")
    print(student_json)
    print()
    print("=== TEACHER VIEW (_format_messages output) ===")
    print(teacher_view)
    print()

    # --- Assertions ---

    # 1. Every user message content is present.
    for msg in student_view:
        if msg["role"] == "user":
            assert msg["content"] in teacher_view, (
                f"User content missing from teacher view: {msg['content'][:100]}"
            )

    # 2. Every assistant text content is present.
    for msg in student_view:
        if msg["role"] == "assistant" and msg.get("content"):
            assert msg["content"] in teacher_view, (
                f"Assistant content missing from teacher view: {msg['content'][:100]}"
            )

    # 3. Every tool call name and arguments are present.
    for msg in student_view:
        if msg["role"] == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                fn = tc["function"]
                assert fn["name"] in teacher_view, (
                    f"Tool call name missing: {fn['name']}"
                )
                # Arguments as JSON string — the teacher shows json.dumps(arguments_dict).
                # The student has json.dumps(dict) too, so they should match.
                assert fn["arguments"] in teacher_view, (
                    f"Tool call arguments missing: {fn['arguments'][:100]}"
                )

    # 4. Every tool result content is present IN FULL (no truncation).
    for msg in student_view:
        if msg["role"] == "tool":
            assert msg["content"] in teacher_view, (
                f"Tool result content missing or truncated. Length={len(msg['content'])}. "
                f"First 200 chars: {msg['content'][:200]}"
            )

    # 5. Tool result labels resolve to correct tool names (not generic "tool").
    assert "[tool_result: get_reservation_details]" in teacher_view
    assert "[tool_result: get_cancellation_policy]" in teacher_view
    assert "[tool_result: cancel_reservation]" in teacher_view
    assert "[tool_result: process_refund]" in teacher_view

    # 6. System message is NOT in the teacher view (shown separately).
    assert "You are a helpful airline agent." not in teacher_view


def test_no_data_loss_long_tool_result():
    """Tool results longer than 500 chars must not be truncated."""
    long_content = "x" * 1000
    messages = [
        AssistantMessage(
            role="assistant",
            content=None,
            tool_calls=[ToolCall(id="c1", name="big_tool", arguments={"q": 1})],
        ),
        ToolMessage(id="c1", role="tool", content=long_content),
    ]
    teacher_view = _format_messages(messages)
    assert long_content in teacher_view, "Long tool result was truncated!"


def test_assistant_content_with_tool_calls():
    """When assistant sends both text and tool calls, both must appear."""
    messages = [
        AssistantMessage(
            role="assistant",
            content="Thinking out loud before calling tool...",
            tool_calls=[
                ToolCall(id="c1", name="some_tool", arguments={"a": 1}),
            ],
        ),
        ToolMessage(id="c1", role="tool", content="result"),
    ]
    teacher_view = _format_messages(messages)
    assert "Thinking out loud before calling tool..." in teacher_view
    assert "some_tool" in teacher_view
    assert '{"a": 1}' in teacher_view
