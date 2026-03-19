#!/usr/bin/env python3
"""Generate slide-friendly (16:9 landscape) versions of thesis diagrams.

Redraws the 10 figures that were portrait or near-square in the thesis
into horizontal layouts suitable for 16:9 presentation slides.

Usage:  cd slides && uv run python gen_slide_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent so we can reuse diagram_style
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "text"))

from diagram_style import *  # noqa: E402

# Override output directory
OUTPUT_DIR = "figures"


# ===================================================================
# fig_01_outer_loop — was TB (0.46:1), now LR
# ===================================================================

def fig_01_outer_loop():
    """Evolution outer loop — horizontal layout."""
    g = new_graph("slide_fig_01_outer_loop", rankdir="LR")
    g.attr(nodesep="0.5", ranksep="0.8")

    terminal_node(g, "start", "Start\n(sweep = 1)")
    process_node(g, "eval", "Evaluate student\non all tasks\n(N trials each)")
    data_node(g, "results", "Evaluation\nresults")
    process_node(g, "extract", "Extract\nfailures\n(trial < 1.0)")
    decision_node(g, "any_fail", "Failures\nremain?")
    process_node(g, "fix", "Fix failures\nin parallel\n(teacher sessions)")
    process_node(g, "merge", "Merge via\nmerger LLM")
    decision_node(g, "max_iter", "Max sweeps\nreached?")
    terminal_node(g, "end", "End\n(evolved state)")

    g.edge("start", "eval")
    g.edge("eval", "results")
    g.edge("results", "extract")
    g.edge("extract", "any_fail")
    g.edge("any_fail", "fix", label="Yes")
    g.edge("any_fail", "end", label="No", style="dashed")
    g.edge("fix", "merge")
    g.edge("merge", "max_iter")
    g.edge("max_iter", "end", label="Yes", style="dashed")

    # Loop-back edge — below the main flow
    g.edge("max_iter", "eval", label="No\n(re-evaluate)",
           constraint="false", style="dashed",
           color=BLUE, fontcolor=BLUE)

    render(g)


# ===================================================================
# fig_02_inner_loop — was TB (0.44:1), now LR
# ===================================================================

def fig_02_inner_loop():
    """Per-failure fix loop — horizontal layout."""
    g = new_graph("slide_fig_02_inner_loop", rankdir="LR")
    g.attr(nodesep="0.4", ranksep="0.7")

    terminal_node(g, "start", "Failed task\nreceived")
    process_node(g, "copy", "Deep-copy\ncurrent state")
    process_node(g, "reflect", "Teacher\nanalyzes trace")
    process_node(g, "patch", "Teacher calls\npatch tools")
    process_node(g, "validate", "Re-run student\n(N trials)")
    decision_node(g, "improved", "All trials\npass?")
    highlight_node(g, "accept", "Accept\npatches", color=C["success"])
    decision_node(g, "retries", "Retries\nleft?")
    process_node(g, "revert", "Revert\npatches")
    highlight_node(g, "reject", "Discard\npatches", color=C["failure"])

    g.edge("start", "copy")
    g.edge("copy", "reflect")
    g.edge("reflect", "patch")
    g.edge("patch", "validate")
    g.edge("validate", "improved")
    g.edge("improved", "accept", label="Yes")
    g.edge("improved", "retries", label="No")
    g.edge("retries", "reject", label="No", style="dashed")
    g.edge("retries", "revert", label="Yes")

    # Loop-back: revert -> reflect
    g.edge("revert", "reflect", label="+ feedback",
           constraint="false", style="dashed",
           color=BLUE, fontcolor=BLUE)

    render(g)


# ===================================================================
# fig_04_teacher_session — was TB near-square (1.17:1), now LR
# ===================================================================

def fig_04_teacher_session():
    """Teacher session tool-calling sequence — horizontal layout."""
    g = new_graph("slide_fig_04_teacher_session", rankdir="LR")
    g.attr(nodesep="0.4", ranksep="0.9")

    data_node(g, "context", "Context Package\n"
              "- System prompt\n"
              "- Tool schemas\n"
              "- Failed trace\n"
              "- Task requirements\n"
              "- Reward breakdown")

    process_node(g, "diagnose", "Diagnose\nroot cause +\nclassify failure")
    process_node(g, "call_tools", "Call patch tools\n(1..N per round)")

    # Tool cluster — horizontal
    tools = cluster(g, "tools", "  Available Tools  ")
    highlight_node(tools, "pp", "patch_prompt", color="#D6EAF8")
    highlight_node(tools, "pt", "patch_tool", color="#D6EAF8")
    highlight_node(tools, "rtc", "read_tool_code", color="#D6EAF8")
    highlight_node(tools, "ptc", "patch_tool_code\n(Phase 2 only)", color="#FADBD8")
    g.subgraph(tools)

    process_node(g, "apply", "Apply patches\nto local state")
    decision_node(g, "more", "More\ncalls?")
    data_node(g, "output", "Patched state\n+ diagnosis")

    g.edge("context", "diagnose")
    g.edge("diagnose", "call_tools")
    g.edge("call_tools", "pp", style="dashed", arrowhead="none")
    g.edge("call_tools", "pt", style="dashed", arrowhead="none")
    g.edge("call_tools", "rtc", style="dashed", arrowhead="none")
    g.edge("call_tools", "ptc", style="dashed", arrowhead="none")
    g.edge("call_tools", "apply")
    g.edge("apply", "more")
    g.edge("more", "output", label="No / max\nrounds")
    g.edge("more", "call_tools", label="Yes",
           constraint="false", style="dashed",
           color=BLUE, fontcolor=BLUE)

    render(g)


# ===================================================================
# fig_06_patch_surfaces — was LR but near-square (1.15:1), widen
# ===================================================================

def fig_06_patch_surfaces():
    """Patch surfaces and failure type mapping — wider layout."""
    g = new_graph("slide_fig_06_patch_surfaces", rankdir="LR")
    g.attr(nodesep="0.3", ranksep="1.4")

    # Failure types column
    fails = cluster(g, "failures", "  Failure Types  ")
    fails.node("tm", label="TOOL_MISUSE", shape="box", style="filled,rounded",
               fillcolor=VERMILLION, fontcolor="white", fontname=FONT_BOLD,
               width="2.2")
    fails.node("pv", label="POLICY_VIOLATION", shape="box", style="filled,rounded",
               fillcolor=ORANGE, fontname=FONT_BOLD, width="2.2")
    fails.node("re", label="REASONING_ERROR", shape="box", style="filled,rounded",
               fillcolor=BLUE, fontcolor="white", fontname=FONT_BOLD, width="2.2")
    fails.node("ce", label="COMMUNICATION_ERROR", shape="box", style="filled,rounded",
               fillcolor=GREEN, fontcolor="white", fontname=FONT_BOLD, width="2.2")
    g.subgraph(fails)

    # Patch surfaces column — side by side using rank constraints
    surfs = cluster(g, "surfaces", "  Patch Surfaces  ")
    surfs.node("prompt_patch",
               label="Prompt Patches\nBehavioral rules, policy\nconstraints, tool-use hints",
               shape="box", style="filled,rounded", fillcolor="#D6EAF8",
               width="3.0", height="1.0")
    surfs.node("schema_patch",
               label="Tool Schema Patches\nParameter descriptions,\nconstraint notes, usage hints",
               shape="box", style="filled,rounded", fillcolor="#D5F5E3",
               width="3.0", height="1.0")
    surfs.node("code_patch",
               label="Tool Preprocessors\nInput coercion, format\nnormalization, guardrails",
               shape="box", style="filled,rounded", fillcolor="#FADBD8",
               width="3.0", height="1.0")
    g.subgraph(surfs)

    # Mappings
    g.edge("pv", "prompt_patch", color=ORANGE, penwidth="1.5")
    g.edge("re", "prompt_patch", color=BLUE, penwidth="1.5")
    g.edge("ce", "prompt_patch", color=GREEN, penwidth="1.5")
    g.edge("tm", "schema_patch", color=VERMILLION, penwidth="1.5")
    g.edge("re", "schema_patch", color=BLUE, penwidth="1.5", style="dashed")
    g.edge("tm", "code_patch", color=VERMILLION, penwidth="1.5", style="dashed")

    render(g)


# ===================================================================
# fig_07_conversation_mechanics — was TB (0.61:1), now LR
# ===================================================================

def fig_07_conversation_mechanics():
    """Conversation mechanics — horizontal layout."""
    g = new_graph("slide_fig_07_conversation_mechanics", rankdir="LR")
    g.attr(nodesep="0.4", ranksep="0.7")

    terminal_node(g, "start", "Task begins\n(scenario loaded)")
    process_node(g, "user_turn", "User simulator\nsends message")
    process_node(g, "agent_turn", "Agent\nprocesses msg")
    decision_node(g, "action", "Agent\naction?")
    process_node(g, "text", "Send text\nto user")
    process_node(g, "tool", "Invoke tool")
    process_node(g, "exec", "Execute\non sim DB")
    process_node(g, "result", "Return\ntool result")
    decision_node(g, "done", "User signals\ncompletion?")
    terminal_node(g, "eval", "Evaluate\ntask criteria")

    g.edge("start", "user_turn")
    g.edge("user_turn", "agent_turn")
    g.edge("agent_turn", "action")
    g.edge("action", "text", label="text")
    g.edge("action", "tool", label="tool call")
    g.edge("tool", "exec")
    g.edge("exec", "result")
    g.edge("result", "agent_turn", label="another turn",
           constraint="false", style="dashed",
           color=BLUE, fontcolor=BLUE)
    g.edge("text", "done")
    g.edge("done", "eval", label="Yes", style="dashed")
    g.edge("done", "user_turn", label="No",
           constraint="false", style="dashed",
           color=BLUE, fontcolor=BLUE)

    render(g)


# ===================================================================
# fig_09_reward_breakdown — was TB near-square (1.21:1), now LR
# ===================================================================

def fig_09_reward_breakdown():
    """Reward evaluation components — horizontal layout."""
    g = new_graph("slide_fig_09_reward_breakdown", rankdir="LR")
    g.attr(nodesep="0.3", ranksep="0.9")

    data_node(g, "trace", "Completed\nConversation\nTrace")

    # Three evaluation dimensions — stacked vertically in a cluster
    ev = cluster(g, "eval", "  Reward Dimensions  ")
    ev.node("action", label="Action Score\nCorrect tools,\nargs, sequence",
            shape="box", style="filled,rounded", fillcolor="#D6EAF8",
            width="2.2", height="0.9")
    ev.node("env", label="Environment\nAssertions\nExpected DB state",
            shape="box", style="filled,rounded", fillcolor="#D5F5E3",
            width="2.2", height="0.9")
    ev.node("comm", label="Communication\nScore\nUser-facing info",
            shape="box", style="filled,rounded", fillcolor="#FCF3CF",
            width="2.2", height="0.9")
    g.subgraph(ev)

    g.node("combine", label="Combined Reward\n[0.0 - 1.0]",
           shape="box", style="filled,rounded,bold", fillcolor="#EAECEE",
           fontname=FONT_BOLD)

    decision_node(g, "pass", "reward\n= 1.0?")
    highlight_node(g, "yes", "PASS", color=C["success"])
    highlight_node(g, "no", "FAIL", color=C["failure"])

    g.edge("trace", "action")
    g.edge("trace", "env")
    g.edge("trace", "comm")
    g.edge("action", "combine")
    g.edge("env", "combine")
    g.edge("comm", "combine")
    g.edge("combine", "pass")
    g.edge("pass", "yes", label="Yes")
    g.edge("pass", "no", label="No")

    render(g)


# ===================================================================
# fig_10_escalation — was TB (0.32:1, worst), now LR with side-by-side phases
# ===================================================================

def fig_10_escalation():
    """Two-phase teacher escalation — horizontal with side-by-side phases."""
    g = new_graph("slide_fig_10_escalation", rankdir="LR")
    g.attr(nodesep="0.35", ranksep="0.7")

    terminal_node(g, "start", "Task failure\nreceived")

    # Phase 1
    p1 = cluster(g, "phase1", "  Phase 1: Teaching  ")
    process_node(p1, "p1_reflect", "Diagnose\nfailure")
    process_node(p1, "p1_patch", "patch_prompt\npatch_tool\nread_tool_code")
    process_node(p1, "p1_validate", "Validate")
    decision_node(p1, "p1_ok", "Fixed?")
    p1.edge("p1_reflect", "p1_patch")
    p1.edge("p1_patch", "p1_validate")
    p1.edge("p1_validate", "p1_ok")
    g.subgraph(p1)

    decision_node(g, "escalate", "Phase 2\nattempts?")

    # Phase 2
    p2 = cluster(g, "phase2", "  Phase 2: Guardrails  ")
    p2.attr(bgcolor="#FFF5F5")
    process_node(p2, "p2_reflect", "Diagnose\n+ code access")
    process_node(p2, "p2_patch", "patch_prompt\npatch_tool\nread_tool_code\npatch_tool_code")
    p2.node("p2_patch", fillcolor="#FADBD8")
    process_node(p2, "p2_validate", "Validate")
    decision_node(p2, "p2_ok", "Fixed?")
    p2.edge("p2_reflect", "p2_patch")
    p2.edge("p2_patch", "p2_validate")
    p2.edge("p2_validate", "p2_ok")
    g.subgraph(p2)

    highlight_node(g, "accept", "Patches\naccepted", color=C["success"])
    highlight_node(g, "reject", "Patches\ndiscarded", color=C["failure"])

    g.edge("start", "p1_reflect")
    g.edge("p1_ok", "accept", label="Yes")
    g.edge("p1_ok", "escalate", label="No")
    g.edge("escalate", "p2_reflect", label="Yes")
    g.edge("escalate", "reject", label="No", style="dashed")
    g.edge("p2_ok", "accept", label="Yes")
    g.edge("p2_ok", "reject", label="No", style="dashed")

    render(g)


# ===================================================================
# fig_11_parallel_architecture — was TB (0.80:1), now LR
# ===================================================================

def fig_11_parallel_architecture():
    """Parallel execution architecture — horizontal layout."""
    g = new_graph("slide_fig_11_parallel_architecture", rankdir="LR")
    g.attr(nodesep="0.3", ranksep="0.8")

    process_node(g, "eval", "Evaluate\nall tasks")
    process_node(g, "extract", "Extract\nN failures")

    # Parallel threads — stacked vertically
    par = cluster(g, "parallel", "  ThreadPoolExecutor  ")
    par.attr(bgcolor="#F0F4FF")
    for i in range(1, 4):
        sub = cluster(par, f"t{i}", f"  Thread {i}  ")
        sub.attr(bgcolor="white")
        process_node(sub, f"t{i}_copy", "Copy\nstate")
        process_node(sub, f"t{i}_teacher", "Teacher\nsession")
        process_node(sub, f"t{i}_val", "Validate")
        sub.edge(f"t{i}_copy", f"t{i}_teacher")
        sub.edge(f"t{i}_teacher", f"t{i}_val")
        par.subgraph(sub)
    par.node("dots", label="...", shape="plaintext", fontsize="18",
             fontname=FONT_BOLD)
    g.subgraph(par)

    process_node(g, "collect", "Collect\nFixResults")
    process_node(g, "merge", "Merge via\nmerger LLM")
    data_node(g, "state", "Updated\nglobal state")

    g.edge("eval", "extract")
    g.edge("extract", "t1_copy")
    g.edge("extract", "t2_copy")
    g.edge("extract", "t3_copy")
    g.edge("t1_val", "collect")
    g.edge("t2_val", "collect")
    g.edge("t3_val", "collect")
    g.edge("collect", "merge")
    g.edge("merge", "state")

    render(g)


# ===================================================================
# fig_12_patch_pipeline — was TB (0.76:1), now LR
# ===================================================================

def fig_12_patch_pipeline():
    """Patch application pipeline — horizontal with three parallel paths."""
    g = new_graph("slide_fig_12_patch_pipeline", rankdir="LR")
    g.attr(nodesep="0.25", ranksep="0.7")

    process_node(g, "propose", "Teacher proposes\npatch (old, new)")
    decision_node(g, "type", "Patch\ntype?")

    g.edge("propose", "type")

    # Three paths — stacked vertically via clusters
    p_path = cluster(g, "prompt_path", "  Prompt  ")
    process_node(p_path, "p_find", "Find in\nprompt")
    process_node(p_path, "p_replace", "Replace\ntext")
    p_path.edge("p_find", "p_replace")
    g.subgraph(p_path)

    s_path = cluster(g, "schema_path", "  Tool Schema  ")
    process_node(s_path, "s_find", "Find in\nschema JSON")
    process_node(s_path, "s_replace", "Replace\ntext")
    decision_node(s_path, "s_valid", "Valid\nJSON?")
    s_path.edge("s_find", "s_replace")
    s_path.edge("s_replace", "s_valid")
    g.subgraph(s_path)

    c_path = cluster(g, "code_path", "  Preprocessor  ")
    process_node(c_path, "c_find", "Find in\nsource")
    process_node(c_path, "c_replace", "Replace\ntext")
    decision_node(c_path, "c_safe", "Compiles\n& passes\nanalysis?")
    c_path.edge("c_find", "c_replace")
    c_path.edge("c_replace", "c_safe")
    g.subgraph(c_path)

    highlight_node(g, "accept", "Patch\napplied", color=C["success"])
    highlight_node(g, "reject", "Patch\nrejected", color=C["failure"])

    g.edge("type", "p_find", label="prompt")
    g.edge("type", "s_find", label="schema")
    g.edge("type", "c_find", label="code")

    g.edge("p_replace", "accept")
    g.edge("s_valid", "accept", label="Yes")
    g.edge("s_valid", "reject", label="No", style="dashed")
    g.edge("c_safe", "accept", label="Yes")
    g.edge("c_safe", "reject", label="No", style="dashed")

    render(g)


# ===================================================================
# fig_lr_01_argument_flow — was TB (0.53:1), now LR 2-row zigzag
# ===================================================================

def fig_lr_01_argument_flow():
    """Literature review argument structure — horizontal zigzag."""
    g = new_graph("slide_fig_lr_01_argument_flow", rankdir="LR")
    g.attr(nodesep="0.35", ranksep="0.6")

    steps = [
        ("s1", "LLM agents are\nunreliable at\nenterprise scale", "#F8D7DA", "\u00a72.1"),
        ("s2", "Static prompting\nhits a ceiling", "#FCF3CF", "\u00a72.2"),
        ("s3", "Fine-tuning is\nimpractical for rapid\nadaptation", "#FCF3CF", "\u00a72.3"),
        ("s4", "Prompt optimization\nuntested on\ntool-calling", "#D6EAF8", "\u00a72.4"),
        ("s5", "Teacher-student\ndistillation growing\nat prompt level", "#D6EAF8", "\u00a72.5"),
        ("s6", "Nobody combined\nteacher prompt evo\n+ agentic benchmarks", "#D5F5E3", "\u00a72.6"),
    ]

    for nid, label, fill, sec in steps:
        g.node(nid, label=f"{label}\n\n{sec}", shape="box", style="filled,rounded",
               fillcolor=fill, width="2.2", height="1.1",
               fontname=FONT, fontsize="10")

    # Chain edges
    for i in range(len(steps) - 1):
        g.edge(steps[i][0], steps[i + 1][0], penwidth="1.4")

    # Final gap node
    g.node("gap", label="Research Gap\n(this thesis)",
           shape="box", style="filled,rounded,bold",
           fillcolor="#D5F5E3", color=GREEN, penwidth="2.0",
           fontname=FONT_BOLD, fontsize="11", width="2.0")
    g.edge("s6", "gap", penwidth="1.8", color=GREEN, style="bold")

    render(g)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_FIGURES = [
    fig_01_outer_loop,
    fig_02_inner_loop,
    fig_04_teacher_session,
    fig_06_patch_surfaces,
    fig_07_conversation_mechanics,
    fig_09_reward_breakdown,
    fig_10_escalation,
    fig_11_parallel_architecture,
    fig_12_patch_pipeline,
    fig_lr_01_argument_flow,
]


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else []

    Path(OUTPUT_DIR).mkdir(exist_ok=True)

    if targets:
        name_map = {f.__name__: f for f in ALL_FIGURES}
        for t in targets:
            if t in name_map:
                print(f"Generating {t}...")
                name_map[t]()
            else:
                print(f"Unknown figure: {t}")
                print(f"Available: {', '.join(name_map)}")
    else:
        print(f"Generating {len(ALL_FIGURES)} slide figures...")
        for fn in ALL_FIGURES:
            print(f"  {fn.__name__}...")
            fn()
        print("Done!")
