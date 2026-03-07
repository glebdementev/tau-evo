"""EvolvableAgent — LLMAgent subclass with patchable prompt and tool schemas."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
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
    """LLMAgent that supports runtime patching of the system prompt and tool schemas.

    Patch types
    -----------
    - **prompt_patch**: extra rules appended to the agent instruction.
    - **tool_patches**: per-tool overrides for descriptions and parameter descriptions.
      Format: ``{tool_name: {"description": str, "params": {param_name: str}}}``
    """

    def __init__(
        self,
        tools: list[Tool],
        domain_policy: str,
        llm: Optional[str] = None,
        llm_args: Optional[dict] = None,
    ):
        # Extract our custom keys from llm_args before passing to parent.
        # tau2 calls: AgentConstructor(tools=..., domain_policy=..., llm=..., llm_args=...)
        llm_args = dict(llm_args) if llm_args else {}
        self.prompt_patch: Optional[str] = llm_args.pop("prompt_patch", None)
        self.tool_patches: Optional[dict] = llm_args.pop("tool_patches", None)
        super().__init__(tools=tools, domain_policy=domain_policy, llm=llm, llm_args=llm_args or None)
        if self.tool_patches:
            self.tools = self._apply_tool_patches()

    @property
    def system_prompt(self) -> str:
        instruction = AGENT_INSTRUCTION
        if self.prompt_patch:
            instruction += "\n\n## Learned Rules\n" + self.prompt_patch
        return SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy,
            agent_instruction=instruction,
        )

    def _apply_tool_patches(self) -> list:
        """Return tools with description / param-description overrides applied."""
        patched = []
        for tool in self.tools:
            if tool.name not in self.tool_patches:
                patched.append(tool)
                continue

            patch = self.tool_patches[tool.name]
            schema = deepcopy(tool.openai_schema)

            if "description" in patch:
                schema["function"]["description"] = patch["description"]
            if "params" in patch:
                props = schema["function"]["parameters"].get("properties", {})
                for param_name, new_desc in patch["params"].items():
                    if param_name in props:
                        props[param_name]["description"] = new_desc

            patched.append(PatchedTool(tool, schema))

        return patched

    # ── Serialisation helpers ────────────────────────────────────────────

    def save_patches(self, path: Path) -> None:
        data = {
            "prompt_patch": self.prompt_patch,
            "tool_patches": self.tool_patches,
        }
        path.write_text(json.dumps(data, indent=2))

    @staticmethod
    def load_patches(path: Path) -> dict:
        return json.loads(path.read_text())


# Register with tau2 so RunConfig can reference it by name.
registry.register_agent(EvolvableAgent, "evolvable_agent")
