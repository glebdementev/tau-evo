"""EvolvableAgent — LLMAgent subclass with patchable prompt and tool schemas."""

from __future__ import annotations

from typing import Optional

from tau2.agent.llm_agent import LLMAgent, SYSTEM_PROMPT, AGENT_INSTRUCTION
from tau2.environment.tool import Tool
from tau2.registry import registry


class PatchedTool:
    """Wrapper that delegates everything to the original tool but overrides openai_schema."""

    def __init__(self, original: Tool, schema: dict):
        self._original = original
        self._schema = schema

    @property
    def openai_schema(self) -> dict:
        return self._schema

    @property
    def name(self) -> str:
        return self._original.name

    def __call__(self, *args, **kwargs):
        return self._original(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._original, name)


class EvolvableAgent(LLMAgent):
    """LLMAgent that supports runtime patching of the system prompt and tool schemas."""

    def __init__(
        self,
        tools: list[Tool],
        domain_policy: str,
        llm: Optional[str] = None,
        llm_args: Optional[dict] = None,
    ):
        llm_args = dict(llm_args) if llm_args else {}
        self.prompt_instruction: Optional[str] = llm_args.pop("prompt_instruction", None)
        self._system_prompt_override: Optional[str] = llm_args.pop("system_prompt", None)
        tool_schemas: Optional[dict] = llm_args.pop("tool_schemas", None)
        super().__init__(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args or None)
        if tool_schemas:
            self.tools = self._apply_tool_schemas(tool_schemas)

    @property
    def system_prompt(self) -> str:
        if self._system_prompt_override is not None:
            return self._system_prompt_override
        return SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy,
            agent_instruction=self.prompt_instruction or AGENT_INSTRUCTION,
        )

    def _apply_tool_schemas(self, tool_schemas: dict) -> list:
        """Return tools with full schema overrides applied."""
        patched = []
        for tool in self.tools:
            if tool.name in tool_schemas:
                patched.append(PatchedTool(tool, tool_schemas[tool.name]))
            else:
                patched.append(tool)
        return patched


# Register with tau2 so RunConfig can reference it by name.
registry.register_agent(EvolvableAgent, "evolvable_agent")
