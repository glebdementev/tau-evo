"""Pydantic tool models for the teacher's tool-calling interface."""

from openai.lib._tools import pydantic_function_tool
from pydantic import BaseModel, Field


class PatchPrompt(BaseModel):
    """Replace text in the agent's system prompt. Use old_text='' and new_text='...' to insert new text at the end."""

    old_text: str = Field(
        description="Exact text to find in the current prompt. Empty string to append.",
    )
    new_text: str = Field(
        description="Replacement text. Empty string to delete the old_text.",
    )


class PatchTool(BaseModel):
    """Replace text in a tool's schema (description or parameter description)."""

    tool_name: str = Field(description="Name of the tool to patch.")
    old_text: str = Field(description="Exact text to find in the tool's schema JSON.")
    new_text: str = Field(description="Replacement text.")


class ReadToolCode(BaseModel):
    """Read a tool's parameter details, docstring info, and current input preprocessor.

    Use this to understand a tool's expected input formats, return types, raised exceptions,
    and to see the current preprocessor code before editing it.
    NOTE: The tool's implementation source code is not shown — only its public API contract.
    """

    tool_name: str = Field(description="Name of the tool to inspect.")


class PatchToolCode(BaseModel):
    """Edit a tool's input preprocessor using find-and-replace.

    The preprocessor is a Python function `preprocess(kwargs) -> kwargs` that transforms
    the tool's input arguments BEFORE the tool executes. Use it to add input coercion
    (e.g. adding '#' prefix to IDs, casting strings to ints, normalizing formats).

    The preprocessor can ONLY modify inputs — it cannot change the tool's output.
    Use old_text='' to append code at the end of the preprocessor.
    """

    tool_name: str = Field(description="Name of the tool to patch.")
    old_text: str = Field(
        description="Exact text to find in the current preprocessor source. Empty string to append.",
    )
    new_text: str = Field(description="Replacement text.")


# Teaching-only tools: prompt and schema edits + read-only tool inspection.
# Used in Phase 1 (escalation tier) to force the teacher to fix agent behavior first.
TEACHING_TOOLS = [
    pydantic_function_tool(PatchPrompt, name="patch_prompt"),
    pydantic_function_tool(PatchTool, name="patch_tool"),
    pydantic_function_tool(ReadToolCode, name="read_tool_code"),
]

# Full tool set including preprocessor editing. Unlocked in Phase 2 after prompt-only fixes fail.
TEACHER_TOOLS = [
    pydantic_function_tool(PatchPrompt, name="patch_prompt"),
    pydantic_function_tool(PatchTool, name="patch_tool"),
    pydantic_function_tool(ReadToolCode, name="read_tool_code"),
    pydantic_function_tool(PatchToolCode, name="patch_tool_code"),
]

TOOL_MODELS = {
    "patch_prompt": PatchPrompt,
    "patch_tool": PatchTool,
    "read_tool_code": ReadToolCode,
    "patch_tool_code": PatchToolCode,
}
