"""EvolvableAgent — LLMAgent subclass with patchable prompt, tool schemas, and tool preprocessors."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from tau2.agent.llm_agent import LLMAgent, SYSTEM_PROMPT, AGENT_INSTRUCTION
from tau2.environment.tool import Tool
from tau2.registry import registry

log = logging.getLogger(__name__)


class PatchedTool:
    """Wrapper that delegates everything to the original tool but overrides openai_schema
    and optionally runs an input preprocessor before calling the original."""

    def __init__(
        self,
        original: Tool,
        schema: Optional[dict] = None,
        preprocess: Optional[Callable] = None,
    ):
        self._original = original
        self._schema = schema
        self._preprocess = preprocess

    @property
    def openai_schema(self) -> dict:
        if self._schema is not None:
            return self._schema
        return self._original.openai_schema

    @property
    def name(self) -> str:
        return self._original.name

    def __call__(self, *args, **kwargs):
        if self._preprocess is not None:
            try:
                kwargs = self._preprocess(kwargs)
            except Exception as e:
                log.warning("Preprocessor for '%s' failed: %s — using original kwargs", self.name, e)
        return self._original(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._original, name)


def _compile_preprocessor_safe(source: str, tool_name: str) -> Optional[Callable]:
    """Compile a preprocessor source string. Returns None if source is default/empty."""
    from evo.reflection.preprocessor import DEFAULT_PREPROCESSOR as _DEFAULT_PREPROCESSOR, compile_preprocessor
    if source.strip() == _DEFAULT_PREPROCESSOR.strip():
        return None
    try:
        return compile_preprocessor(source, tool_name)
    except ValueError as e:
        log.error("Failed to compile preprocessor for '%s': %s", tool_name, e)
        return None


class EvolvableAgent(LLMAgent):
    """LLMAgent that supports runtime patching of the system prompt, tool schemas, and tool code."""

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
        tool_code: Optional[dict[str, str]] = llm_args.pop("tool_code", None)
        super().__init__(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args or None)
        if tool_schemas or tool_code:
            self.tools = self._apply_patches(tool_schemas, tool_code)

    @property
    def system_prompt(self) -> str:
        if self._system_prompt_override is not None:
            return self._system_prompt_override
        return SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy,
            agent_instruction=self.prompt_instruction or AGENT_INSTRUCTION,
        )

    def _apply_patches(
        self,
        tool_schemas: Optional[dict],
        tool_code: Optional[dict[str, str]],
    ) -> list:
        """Return tools with schema overrides and/or preprocessor wrappers applied."""
        tool_schemas = tool_schemas or {}
        tool_code = tool_code or {}

        patched = []
        for tool in self.tools:
            schema = tool_schemas.get(tool.name)
            preprocess = None
            if tool.name in tool_code:
                preprocess = _compile_preprocessor_safe(tool_code[tool.name], tool.name)

            if schema is not None or preprocess is not None:
                patched.append(PatchedTool(tool, schema=schema, preprocess=preprocess))
            else:
                patched.append(tool)
        return patched


# Register with tau2 so RunConfig can reference it by name.
registry.register_agent(EvolvableAgent, "evolvable_agent")
