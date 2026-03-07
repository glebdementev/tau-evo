"""Preprocessor compilation and tool info formatting."""

from __future__ import annotations

import json
import re
from typing import Callable


DEFAULT_PREPROCESSOR = """\
def preprocess(kwargs):
    return kwargs
"""

# Restricted builtins for preprocessor execution — no imports, no eval/exec.
_SAFE_BUILTINS = {
    "str": str, "int": int, "float": float, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "len": len, "isinstance": isinstance, "type": type,
    "max": max, "min": min, "abs": abs, "round": round,
    "sorted": sorted, "reversed": reversed, "enumerate": enumerate,
    "zip": zip, "map": map, "filter": filter, "any": any, "all": all,
    "range": range, "repr": repr,
    "ValueError": ValueError, "TypeError": TypeError, "KeyError": KeyError,
    "True": True, "False": False, "None": None,
    "re": re,  # regex for coercion patterns
    "__import__": None,  # block imports
}


_FORBIDDEN_PATTERNS = re.compile(
    r'\b(import\s|__import__|eval\s*\(|exec\s*\(|compile\s*\('
    r'|globals\s*\(|locals\s*\(|getattr\s*\(|setattr\s*\(|delattr\s*\('
    r'|__builtins__|__class__|__subclasses__|__bases__'
    r'|open\s*\(|print\s*\()',
)


def compile_preprocessor(source: str, tool_name: str) -> Callable:
    """Compile a preprocessor source string into a callable.

    Raises ValueError with a descriptive message if compilation or definition fails.
    """
    # Static check for forbidden constructs.
    match = _FORBIDDEN_PATTERNS.search(source)
    if match:
        raise ValueError(
            f"Forbidden construct in preprocessor for '{tool_name}': '{match.group().strip()}'. "
            f"Preprocessors can only transform kwargs using basic Python operations and `re`."
        )

    try:
        code = compile(source, f"<preprocess:{tool_name}>", "exec")
    except SyntaxError as e:
        raise ValueError(
            f"Syntax error in preprocessor for '{tool_name}' "
            f"at line {e.lineno}: {e.msg}"
        ) from e

    namespace: dict = {"__builtins__": _SAFE_BUILTINS}
    try:
        exec(code, namespace)
    except Exception as e:
        raise ValueError(
            f"Execution error defining preprocessor for '{tool_name}': {e}"
        ) from e

    if "preprocess" not in namespace:
        raise ValueError(
            f"Preprocessor for '{tool_name}' must define a function named 'preprocess'. "
            f"Defined names: {[k for k in namespace if not k.startswith('_')]}"
        )

    func = namespace["preprocess"]
    if not callable(func):
        raise ValueError(
            f"'preprocess' in '{tool_name}' is not callable (got {type(func).__name__})."
        )

    return func


def format_tool_info(tool) -> str:
    """Format a Tool's public API info (no source code) for the teacher."""
    lines = [f"Tool: {tool.name}"]
    lines.append(f"Description: {tool.short_desc}")
    if tool.long_desc and tool.long_desc != tool.short_desc:
        lines.append(f"Details: {tool.long_desc}")

    # Parameter details from Pydantic schema.
    params_schema = tool.params.model_json_schema()
    if "properties" in params_schema:
        lines.append("\nParameters:")
        required = set(params_schema.get("required", []))
        for pname, pinfo in params_schema["properties"].items():
            req = " (required)" if pname in required else " (optional)"
            ptype = pinfo.get("type", pinfo.get("$ref", "any"))
            desc = pinfo.get("description", "")
            lines.append(f"  {pname}: {ptype}{req} — {desc}" if desc else f"  {pname}: {ptype}{req}")

    # Return type.
    returns_schema = tool.returns.model_json_schema()
    if returns_schema.get("properties"):
        lines.append(f"\nReturns: {json.dumps(returns_schema, indent=2)}")

    # Exceptions.
    if hasattr(tool, "raises") and tool.raises:
        lines.append("\nRaises:")
        for exc in tool.raises:
            exc_type = exc.get("type_name", "Exception")
            exc_desc = exc.get("description", "")
            lines.append(f"  {exc_type}: {exc_desc}" if exc_desc else f"  {exc_type}")

    # Examples.
    if hasattr(tool, "examples") and tool.examples:
        lines.append("\nExamples:")
        for ex in tool.examples:
            lines.append(f"  {ex}")

    return "\n".join(lines)
