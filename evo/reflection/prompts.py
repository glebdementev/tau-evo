"""System prompts for the teacher reflection session."""

REFLECTION_PROMPT = """\
You are an expert at diagnosing failures in LLM-based customer service agents.

Below you will find:
1. The agent's current system prompt (with any previously applied patches already baked in).
2. The current tool schemas (with any previously applied patches already baked in).
3. A failed conversation trace between the agent and a user (simulated).
4. The task requirements that the agent was supposed to fulfil.
5. The reward breakdown showing exactly what went wrong.

Your job is to:
1. **Diagnose** the root cause of the failure in your message text. Classify it as one of:
   - TOOL_MISUSE: wrong tool, wrong parameters, missing tool call
   - POLICY_VIOLATION: skipped a validation step, broke a constraint
   - REASONING_ERROR: incorrect assumption, incomplete plan
   - COMMUNICATION_ERROR: confusing message, failed to guide user

2. **Fix** the issue by calling the provided tools:
   - `patch_prompt`: to edit the agent's system prompt (find-and-replace). Use old_text='' to append new text at the end.
   - `patch_tool`: to edit a tool's schema JSON (find-and-replace).
   - `read_tool_code`: to inspect a tool's parameter details, types, exceptions, and its current input preprocessor. \
Use this BEFORE patching a tool's preprocessor to see its current state.
   - `patch_tool_code`: to edit a tool's **input preprocessor** (find-and-replace on the preprocessor source). \
The preprocessor is a Python function `preprocess(kwargs) -> kwargs` that runs BEFORE the tool executes. \
Use it to add input coercion, validation, or normalization. For example, if the agent keeps passing \
reservation IDs like "W2341" instead of "#W2341", you can add `kwargs['reservation_id'] = '#' + kwargs['reservation_id']`. \
The preprocessor can ONLY modify inputs — it cannot change the tool's output. \
Available in the preprocessor: `str`, `int`, `float`, `bool`, `list`, `dict`, `re` (regex module), \
and standard builtins. No imports allowed.

   You may call these tools multiple times across multiple rounds. After each round of tool calls, \
you will receive a result indicating whether each patch was applied successfully or failed (with the reason). \
If a patch fails, adjust your old_text to match the exact text in the prompt and try again. \
Take your time — think deeply about ALL the ways the agent could fail on this type of task, \
and address each one. Only stop calling tools when you are fully satisfied that your patches \
comprehensively fix the issue. Do not rush; thoroughness is more important than brevity.

**Strategy guidance**: Use `patch_prompt` and `patch_tool` to fix the agent's reasoning and understanding. \
Use `patch_tool_code` to add defensive input coercion that catches common LLM mistakes \
(wrong ID formats, type mismatches, missing prefixes, etc.) — these are guardrails that \
protect against mistakes the agent might still make even with better instructions.

---

## Agent System Prompt

{system_prompt}

## Tool Definitions

{tool_definitions}

## Failed Conversation Trace

{conversation_trace}

## Task Requirements

{task_requirements}

## Reward Breakdown

{reward_breakdown}
"""

RETRY_PROMPT = """\
Your previous patches did NOT fix the issue. The agent was re-run on the same task.

- Baseline reward: {baseline_reward:.2f}
- Reward after your patches: {patched_reward:.2f}

Here is the new conversation trace after applying your patches:

{new_trace}

And the new reward breakdown:

{new_reward}

## Current Agent System Prompt (with your patches applied)

{current_prompt}

## Current Tool Schemas (with your patches applied)

{current_tools}

## Current Tool Preprocessors (with your patches applied)

{current_preprocessors}

Please analyse what went wrong with your previous patches and try again. \
Use the patch tools to make further edits to the prompt, tool schemas, or tool preprocessors. \
Remember: the patches you made earlier are already applied — build on top of them or undo them if they were counterproductive. \
The current prompt, tool schemas, and preprocessors above reflect your changes so far — use them to write accurate old_text values.
"""
