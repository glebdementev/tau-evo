#!/usr/bin/env python3
"""Generate ALL thesis methodology diagrams. Run from text/ directory.

Usage:  cd text && uv run python gen_diagrams.py
"""

from diagram_style import *


def fig_01_outer_loop():
    """Figure 3.1 — Evolution outer loop flowchart."""
    g = new_graph("fig_01_outer_loop", rankdir="TB")
    g.attr(label="Figure 3.1: Evolution Outer Loop", labelloc="b",
           fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD)

    terminal_node(g, "start", "Start\n(iteration = 0)")
    process_node(g, "eval", "Evaluate student on\nall non-dropped tasks")
    data_node(g, "results", "Evaluation results\n{task_id: reward}")
    process_node(g, "extract", "Extract failures\n(reward < 1.0)")
    decision_node(g, "any_fail", "Failures\nremain?")
    process_node(g, "fix", "Fix failures in parallel\n(teacher sessions)")
    process_node(g, "merge", "Merge winning patches\ninto global state")
    process_node(g, "drop", "Drop all attempted tasks\n(fixed + unfixed)")
    decision_node(g, "max_iter", "Max iterations\nreached?")
    terminal_node(g, "end", "End\n(return evolved state)")

    g.edge("start", "eval")
    g.edge("eval", "results")
    g.edge("results", "extract")
    g.edge("extract", "any_fail")
    g.edge("any_fail", "fix", label="  Yes")
    g.edge("any_fail", "end", label="No  ", style="dashed")
    g.edge("fix", "merge")
    g.edge("merge", "drop")
    g.edge("drop", "max_iter")
    g.edge("max_iter", "eval", label="  No")
    g.edge("max_iter", "end", label="Yes  ", style="dashed")

    render(g)


def fig_02_inner_loop():
    """Figure 3.2 — Per-failure inner fix loop."""
    g = new_graph("fig_02_inner_loop", rankdir="TB")
    g.attr(label="Figure 3.2: Per-Failure Fix Loop", labelloc="b",
           fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD)

    terminal_node(g, "start", "Failed task received")
    process_node(g, "copy", "Deep-copy current\nglobal state")
    process_node(g, "reflect", "Teacher analyzes\nfailure trace")
    process_node(g, "patch", "Teacher calls\npatch tools")
    process_node(g, "validate", "Re-run student on\ntask with patches")
    decision_node(g, "improved", "Reward\nimproved?")
    highlight_node(g, "accept", "Accept patches\n(FixResult)", color=C["success"])
    decision_node(g, "retries", "Retries\nleft?")
    process_node(g, "feedback", "Feed new trace +\nreward back to teacher")
    highlight_node(g, "reject", "Discard patches\n(unfixed)", color=C["failure"])

    g.edge("start", "copy")
    g.edge("copy", "reflect")
    g.edge("reflect", "patch")
    g.edge("patch", "validate")
    g.edge("validate", "improved")
    g.edge("improved", "accept", label="  Yes")
    g.edge("improved", "retries", label="No  ")
    g.edge("retries", "feedback", label="  Yes")
    g.edge("retries", "reject", label="No  ", style="dashed")
    g.edge("feedback", "reflect")

    render(g)


def fig_03_system_architecture():
    """Figure 3.3 — System architecture overview."""
    g = new_graph("fig_03_system_architecture", rankdir="LR")
    g.attr(label="Figure 3.3: System Architecture", labelloc="b",
           fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.8", ranksep="1.2")

    # tau2-bench orchestrator cluster
    orch = cluster(g, "orch", "  tau2-bench Orchestrator  ")
    process_node(orch, "orchestrator", "Orchestrator")
    process_node(orch, "db", "Simulated\nDatabase")
    orch.edge("orchestrator", "db", dir="both", style="dashed", label="tool calls")
    g.subgraph(orch)

    # Student agent
    highlight_node(g, "student", "Student Agent\n(Qwen3 30B-A3B)", color=C["process"])
    g.node("student", shape="box3d")

    # User sim
    highlight_node(g, "user_sim", "User Simulator\n(Qwen3 30B-A3B)", color="#F0E6FF")
    g.node("user_sim", shape="box3d")

    # Teacher
    highlight_node(g, "teacher", "Teacher Model\n(Kimi K2.5)", color="#FFE8D6")
    g.node("teacher", shape="box3d")

    # Evolved state
    data_node(g, "state", "Evolved State\n(prompt + schemas\n+ preprocessors)")

    # Edges
    g.edge("orchestrator", "student", label="tool results /\nuser messages", dir="both")
    g.edge("orchestrator", "user_sim", label="agent messages /\nscenario", dir="both")
    g.edge("student", "state", label="uses", style="dashed")
    g.edge("teacher", "state", label="patches", color=VERMILLION, penwidth="1.5")
    g.edge("orchestrator", "teacher", label="failed traces", style="dotted")

    render(g)


def fig_04_teacher_session():
    """Figure 3.4 — Teacher session sequence (multi-round tool calling)."""
    g = new_graph("fig_04_teacher_session", rankdir="TB")
    g.attr(label="Figure 3.4: Teacher Session Tool-Calling Sequence", labelloc="b",
           fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.5")

    # Initial context
    data_node(g, "context", "Context Package\n"
              "- Current system prompt\n"
              "- All tool schemas (JSON)\n"
              "- Failed conversation trace\n"
              "- Task requirements\n"
              "- Reward breakdown")

    process_node(g, "diagnose", "Teacher diagnoses\nroot cause + classifies\nfailure type")
    process_node(g, "call_tools", "Teacher calls patch tools\n(1..N tool calls per round)")

    # Tool calls cluster
    tools = cluster(g, "tools", "  Available Tools  ")
    highlight_node(tools, "pp", "patch_prompt", color="#D6EAF8")
    highlight_node(tools, "pt", "patch_tool", color="#D6EAF8")
    highlight_node(tools, "rtc", "read_tool_code", color="#D6EAF8")
    highlight_node(tools, "ptc", "patch_tool_code", color="#FADBD8")
    tools.node("ptc", xlabel="Phase 2 only")
    g.subgraph(tools)

    process_node(g, "apply", "Apply patches to\nsession-local state")
    decision_node(g, "more", "More tool\ncalls?")
    data_node(g, "output", "Patched state +\ndiagnosis returned")

    g.edge("context", "diagnose")
    g.edge("diagnose", "call_tools")
    g.edge("call_tools", "pp", style="dashed", arrowhead="none")
    g.edge("call_tools", "pt", style="dashed", arrowhead="none")
    g.edge("call_tools", "rtc", style="dashed", arrowhead="none")
    g.edge("call_tools", "ptc", style="dashed", arrowhead="none")
    g.edge("call_tools", "apply")
    g.edge("apply", "more")
    g.edge("more", "call_tools", label="  Yes")
    g.edge("more", "output", label="No (or\nmax rounds)")

    render(g)


def fig_05_three_conditions():
    """Figure 3.5 — Three experimental conditions with gap closure."""
    g = new_graph("fig_05_three_conditions", rankdir="TB")
    g.attr(label="Figure 3.5: Experimental Conditions and Gap Closure",
           labelloc="b", fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.8", ranksep="0.7")

    # Same rank for B, K, F
    with g.subgraph() as s:
        s.attr(rank="same")
        s.node("B", label="Condition B: Baseline\n\nStudent model\ndefault prompt\ndefault tools",
               shape="box", style="filled,rounded,bold", fillcolor="#E8E8E8",
               color=GREY, fontname=FONT, width="2.6", height="1.6")
        s.node("K", label="Condition K: Evolved\n\nStudent model\nevolved prompt\npatched tools",
               shape="box", style="filled,rounded,bold", fillcolor="#D6EAF8",
               color=BLUE, fontname=FONT, width="2.6", height="1.6")
        s.node("F", label="Condition F: Frontier\n\nTeacher model\ndefault prompt\ndefault tools",
               shape="box", style="filled,rounded,bold", fillcolor="#E8DAEF",
               color=PURPLE, fontname=FONT, width="2.6", height="1.6")

    g.edge("B", "K", label="prompt evolution\n(intervention)",
           color=BLUE, penwidth="2.0", fontcolor=BLUE)
    g.edge("K", "F", label="remaining gap",
           color=PURPLE, penwidth="1.5", style="dashed", fontcolor=PURPLE)

    # Labels
    g.node("floor", label="Performance Floor", shape="plaintext",
           fontsize=FONT_SIZE_SMALL, fontcolor=GREY)
    g.node("ceil", label="Performance Ceiling", shape="plaintext",
           fontsize=FONT_SIZE_SMALL, fontcolor=GREY)
    g.edge("floor", "B", style="dotted", arrowhead="none", color=GREY)
    g.edge("ceil", "F", style="dotted", arrowhead="none", color=GREY)

    # Gap closure formula
    g.node("gap", label="Gap Closure = (K − B) / (F − B) × 100%",
           shape="note", style="filled", fillcolor="#FFF9E6",
           fontname=FONT_MONO, fontsize="10", color=ORANGE, width="4.5")
    g.edge("K", "gap", style="dotted", arrowhead="none", color=ORANGE)

    render(g)


def fig_06_patch_surfaces():
    """Figure 3.6 — Three patch surfaces with failure type mapping."""
    g = new_graph("fig_06_patch_surfaces", rankdir="LR")
    g.attr(label="Figure 3.6: Patch Surfaces and Failure Type Mapping",
           labelloc="b", fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.4", ranksep="1.0")

    # Failure types
    fails = cluster(g, "failures", "  Failure Types  ")
    fails.node("tm", label="TOOL_MISUSE", shape="box", style="filled,rounded",
               fillcolor=VERMILLION, fontcolor="white", fontname=FONT_BOLD)
    fails.node("pv", label="POLICY_VIOLATION", shape="box", style="filled,rounded",
               fillcolor=ORANGE, fontname=FONT_BOLD)
    fails.node("re", label="REASONING_ERROR", shape="box", style="filled,rounded",
               fillcolor=BLUE, fontcolor="white", fontname=FONT_BOLD)
    fails.node("ce", label="COMMUNICATION_ERROR", shape="box", style="filled,rounded",
               fillcolor=GREEN, fontcolor="white", fontname=FONT_BOLD)
    g.subgraph(fails)

    # Patch surfaces
    surfs = cluster(g, "surfaces", "  Patch Surfaces  ")

    s1 = cluster(surfs, "prompt", "")
    s1.node("prompt_patch", label="Prompt Patches\n\nAdd behavioral rules\nPolicy constraints\nTool-use instructions",
            shape="box", style="filled,rounded", fillcolor="#D6EAF8",
            width="2.8", height="1.2")
    surfs.subgraph(s1)

    s2 = cluster(surfs, "schema", "")
    s2.node("schema_patch", label="Tool Schema Patches\n\nParameter descriptions\nConstraint notes\nUsage clarifications",
            shape="box", style="filled,rounded", fillcolor="#D5F5E3",
            width="2.8", height="1.2")
    surfs.subgraph(s2)

    s3 = cluster(surfs, "code", "")
    s3.node("code_patch", label="Tool Preprocessors\n\nInput coercion\nFormat normalization\nDefensive guardrails",
            shape="box", style="filled,rounded", fillcolor="#FADBD8",
            width="2.8", height="1.2")
    surfs.subgraph(s3)

    g.subgraph(surfs)

    # Mappings (failure -> surface)
    g.edge("pv", "prompt_patch", color=ORANGE, penwidth="1.5")
    g.edge("re", "prompt_patch", color=BLUE, penwidth="1.5")
    g.edge("ce", "prompt_patch", color=GREEN, penwidth="1.5")
    g.edge("tm", "schema_patch", color=VERMILLION, penwidth="1.5")
    g.edge("re", "schema_patch", color=BLUE, penwidth="1.5", style="dashed")
    g.edge("tm", "code_patch", color=VERMILLION, penwidth="1.5", style="dashed")

    render(g)


def fig_07_conversation_mechanics():
    """Figure 3.7 — tau2-bench conversation mechanics."""
    g = new_graph("fig_07_conversation_mechanics", rankdir="TB")
    g.attr(label="Figure 3.7: Conversation Mechanics (per Task)",
           labelloc="b", fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.4")

    terminal_node(g, "start", "Task begins\n(scenario loaded)")

    process_node(g, "user_turn", "User simulator\nsends message")
    process_node(g, "agent_turn", "Agent processes\nmessage")
    decision_node(g, "action", "Agent\naction?")
    process_node(g, "text", "Send text\nresponse to user")
    process_node(g, "tool", "Invoke tool\nwith arguments")
    process_node(g, "exec", "Execute against\nsimulated DB")
    process_node(g, "result", "Return tool result\nto agent")

    decision_node(g, "done", "User signals\ncompletion?")
    terminal_node(g, "eval", "Evaluate against\ntask criteria")

    g.edge("start", "user_turn")
    g.edge("user_turn", "agent_turn")
    g.edge("agent_turn", "action")
    g.edge("action", "text", label="  text  ")
    g.edge("action", "tool", label="  tool call  ")
    g.edge("tool", "exec")
    g.edge("exec", "result")
    g.edge("result", "agent_turn", style="dashed",
           label="  (agent gets\n  another turn)")
    g.edge("text", "done")
    g.edge("done", "user_turn", label="  No")
    g.edge("done", "eval", label="Yes  ", style="dashed")

    render(g)


def fig_08_failure_taxonomy():
    """Figure 3.8 — Failure taxonomy tree."""
    g = new_graph("fig_08_failure_taxonomy", rankdir="LR")
    g.attr(label="Figure 3.8: Failure Taxonomy", labelloc="b",
           fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.25", ranksep="0.9")

    # Root
    g.node("root", label="Agent\nFailure", shape="box",
           style="filled,rounded,bold", fillcolor="#2C3E50",
           fontcolor="white", fontname=FONT_BOLD, fontsize="12",
           width="1.4", height="1.0")

    # Categories — vertical stacking via LR rankdir
    cats = [
        ("tm", "TOOL_MISUSE", VERMILLION, "white",
         ["Wrong tool selected", "Wrong parameters", "Missing tool call"]),
        ("pv", "POLICY_VIOLATION", ORANGE, "#1A1A2E",
         ["Skipped validation step", "Broke domain constraint", "Wrong action sequence"]),
        ("re", "REASONING_ERROR", BLUE, "white",
         ["Incorrect assumption", "Incomplete plan", "Wrong inference"]),
        ("ce", "COMMUNICATION_ERROR", GREEN, "white",
         ["Confusing message", "Missing information", "Failed to guide user"]),
    ]

    for cid, label, color, fontcolor, examples in cats:
        g.node(cid, label=label, shape="box", style="filled,rounded,bold",
               fillcolor=color, fontcolor=fontcolor, fontname=FONT_BOLD,
               fontsize="10", width="2.4", height="0.5")
        g.edge("root", cid, penwidth="1.5")

        # Examples as a single record node for compactness
        ex_label = "\\l".join(f"  {e}" for e in examples) + "\\l"
        eid = f"{cid}_examples"
        g.node(eid, label=ex_label, shape="box", style="filled,rounded",
               fillcolor="#F8F9FA", fontsize=FONT_SIZE_SMALL,
               fontname=FONT, width="2.2")
        g.edge(cid, eid, arrowhead="none", style="dashed")

    render(g)


def fig_09_reward_breakdown():
    """Figure 3.9 — Reward evaluation components."""
    g = new_graph("fig_09_reward_breakdown", rankdir="TB")
    g.attr(label="Figure 3.9: Task Evaluation and Reward Breakdown",
           labelloc="b", fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.5")

    data_node(g, "trace", "Completed\nConversation Trace")

    # Three evaluation dimensions
    ev = cluster(g, "eval", "  Reward Dimensions  ")
    ev.node("action", label="Action Score\n\nCorrect tools\nCorrect arguments\nCorrect sequence",
            shape="box", style="filled,rounded", fillcolor="#D6EAF8",
            width="2.2", height="1.2")
    ev.node("env", label="Environment\nAssertions\n\nExpected DB state\nPost-conditions",
            shape="box", style="filled,rounded", fillcolor="#D5F5E3",
            width="2.2", height="1.2")
    ev.node("comm", label="Communication\nScore\n\nCorrect messages\nUser-facing info",
            shape="box", style="filled,rounded", fillcolor="#FCF3CF",
            width="2.2", height="1.2")
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
    g.edge("pass", "yes", label="  Yes")
    g.edge("pass", "no", label="No  ")

    render(g)


def fig_10_escalation():
    """Figure 3.10 — Teacher two-phase escalation strategy."""
    g = new_graph("fig_10_escalation", rankdir="TB")
    g.attr(label="Figure 3.10: Two-Phase Teacher Escalation", labelloc="b",
           fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.4")

    terminal_node(g, "start", "Task failure received")

    # Phase 1
    p1 = cluster(g, "phase1", "  Phase 1: Teaching  ")
    process_node(p1, "p1_reflect", "Teacher diagnoses\nfailure")
    process_node(p1, "p1_patch", "patch_prompt\npatch_tool\nread_tool_code")
    process_node(p1, "p1_validate", "Validate on task")
    decision_node(p1, "p1_ok", "Fixed?")
    g.subgraph(p1)

    decision_node(g, "escalate", "Phase 2\nattempts left?")

    # Phase 2
    p2 = cluster(g, "phase2", "  Phase 2: Guardrails  ")
    p2.attr(bgcolor="#FFF5F5")
    process_node(p2, "p2_reflect", "Teacher diagnoses\nwith code access")
    process_node(p2, "p2_patch", "patch_prompt\npatch_tool\nread_tool_code\npatch_tool_code")
    p2.node("p2_patch", fillcolor="#FADBD8")
    process_node(p2, "p2_validate", "Validate on task")
    decision_node(p2, "p2_ok", "Fixed?")
    g.subgraph(p2)

    highlight_node(g, "accept", "Patches accepted", color=C["success"])
    highlight_node(g, "reject", "Patches discarded", color=C["failure"])

    g.edge("start", "p1_reflect")
    g.edge("p1_reflect", "p1_patch")
    g.edge("p1_patch", "p1_validate")
    g.edge("p1_validate", "p1_ok")
    g.edge("p1_ok", "accept", label="  Yes")
    g.edge("p1_ok", "escalate", label="No  ")
    g.edge("escalate", "p2_reflect", label="  Yes")
    g.edge("escalate", "reject", label="No  ", style="dashed")
    g.edge("p2_reflect", "p2_patch")
    g.edge("p2_patch", "p2_validate")
    g.edge("p2_validate", "p2_ok")
    g.edge("p2_ok", "accept", label="  Yes")
    g.edge("p2_ok", "reject", label="No  ", style="dashed")

    render(g)


def fig_11_parallel_architecture():
    """Figure 3.11 — Parallel execution architecture."""
    g = new_graph("fig_11_parallel_architecture", rankdir="TB")
    g.attr(label="Figure 3.11: Parallel Execution Architecture",
           labelloc="b", fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.5")

    process_node(g, "eval", "Evaluate all tasks\n(parallel via tau2)")
    process_node(g, "extract", "Extract N failures")

    # Parallel threads
    par = cluster(g, "parallel", "  ThreadPoolExecutor (max_workers = parallelism)  ")
    par.attr(bgcolor="#F0F4FF")
    for i in range(1, 4):
        sub = cluster(par, f"t{i}", f"  Thread {i}  ")
        sub.attr(bgcolor="white")
        process_node(sub, f"t{i}_copy", "Deep-copy state")
        process_node(sub, f"t{i}_teacher", "Teacher session")
        process_node(sub, f"t{i}_val", "Validate patches")
        sub.edge(f"t{i}_copy", f"t{i}_teacher")
        sub.edge(f"t{i}_teacher", f"t{i}_val")
        par.subgraph(sub)

    # Thread N (ellipsis)
    par.node("dots", label="...", shape="plaintext", fontsize="18",
             fontname=FONT_BOLD)

    g.subgraph(par)

    process_node(g, "collect", "Collect FixResults")
    process_node(g, "merge", "Merge winners\n(sequential)")
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


def fig_12_patch_pipeline():
    """Figure 3.12 — Patch application and validation pipeline."""
    g = new_graph("fig_12_patch_pipeline", rankdir="TB")
    g.attr(label="Figure 3.12: Patch Application Pipeline",
           labelloc="b", fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.4", ranksep="0.6")

    process_node(g, "propose", "Teacher proposes patch\n(old_text, new_text)")
    decision_node(g, "type", "Patch\ntype?")

    g.edge("propose", "type")

    # Three parallel paths in clusters
    p_path = cluster(g, "prompt_path", "  Prompt  ")
    process_node(p_path, "p_find", "Find old_text\nin prompt")
    process_node(p_path, "p_replace", "Replace with\nnew_text")
    p_path.edge("p_find", "p_replace")
    g.subgraph(p_path)

    s_path = cluster(g, "schema_path", "  Tool Schema  ")
    process_node(s_path, "s_find", "Find old_text\nin schema JSON")
    process_node(s_path, "s_replace", "Replace with\nnew_text")
    decision_node(s_path, "s_valid", "Valid\nJSON?")
    s_path.edge("s_find", "s_replace")
    s_path.edge("s_replace", "s_valid")
    g.subgraph(s_path)

    c_path = cluster(g, "code_path", "  Preprocessor  ")
    process_node(c_path, "c_find", "Find old_text in\npreprocessor source")
    process_node(c_path, "c_replace", "Replace with\nnew_text")
    decision_node(c_path, "c_safe", "Passes static\nanalysis?")
    c_path.edge("c_find", "c_replace")
    c_path.edge("c_replace", "c_safe")
    g.subgraph(c_path)

    highlight_node(g, "accept", "Patch applied", color=C["success"])
    highlight_node(g, "reject", "Patch rejected", color=C["failure"])

    g.edge("type", "p_find", label="prompt  ")
    g.edge("type", "s_find", label="schema")
    g.edge("type", "c_find", label="  code")

    g.edge("p_replace", "accept")
    g.edge("s_valid", "accept", label="Yes")
    g.edge("s_valid", "reject", label="No", style="dashed")
    g.edge("c_safe", "accept", label="Yes")
    g.edge("c_safe", "reject", label="No", style="dashed")

    render(g)


def fig_13_gap_closure():
    """Figure 3.13 — Gap closure metric visualization (matplotlib)."""
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from pathlib import Path

    fig, ax = plt.subplots(figsize=(8, 3.5))

    # Example values
    B, K, F = 0.42, 0.64, 0.82
    gap_closure = (K - B) / (F - B) * 100

    y = 0.5
    bar_h = 0.2

    # Full bar (B to F) — light grey
    ax.barh(y, F - B, left=B, height=bar_h, color="#E8E8E8",
            edgecolor="#CCCCCC", linewidth=1)
    # Closed portion (B to K) — blue
    ax.barh(y, K - B, left=B, height=bar_h, color=SKY,
            edgecolor=BLUE, linewidth=1.2, alpha=0.85)

    # Markers
    for val, label, color in [
        (B, f"B = {B:.0%}", GREY),
        (K, f"K = {K:.0%}", BLUE),
        (F, f"F = {F:.0%}", PURPLE),
    ]:
        ax.plot(val, y, "o", color=color, markersize=10, zorder=5)
        ax.annotate(label, (val, y), textcoords="offset points",
                    xytext=(0, 20), ha="center", fontsize=11,
                    fontweight="bold", color=color, fontfamily="serif")

    # Gap closure label
    mid = (B + K) / 2
    ax.annotate(f"Gap Closure = {gap_closure:.0f}%", (mid, y),
                textcoords="offset points", xytext=(0, -26),
                ha="center", fontsize=10, fontfamily="serif",
                color=BLUE, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#E8F4FD",
                          edgecolor=BLUE, alpha=0.9))

    # Remaining gap label
    mid2 = (K + F) / 2
    ax.annotate("Remaining gap", (mid2, y),
                textcoords="offset points", xytext=(0, -26),
                ha="center", fontsize=10, fontfamily="serif",
                color=GREY, fontstyle="italic")

    # Formula below chart
    ax.text(0.5, 0.08, r"Gap Closure $= \frac{K - B}{F - B} \times 100\%$",
            transform=ax.transAxes, ha="center", fontsize=12,
            color="#555555",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#FFF9E6",
                      edgecolor=ORANGE, alpha=0.8))

    ax.set_xlim(0.3, 0.95)
    ax.set_ylim(0.0, 1.0)
    ax.set_xlabel(r"Pass Rate (pass$^1$)", fontsize=11, fontfamily="serif")
    ax.set_yticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    fig.suptitle("Figure 3.13: Gap Closure Metric", fontsize=13,
                 fontweight="bold", fontfamily="serif", y=0.98)

    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    out = f"{OUTPUT_DIR}/fig_13_gap_closure.png"
    fig.savefig(out, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {out}")


def fig_14_knowledge_transfer():
    """Figure 3.14 — Knowledge transfer spectrum positioning."""
    g = new_graph("fig_14_knowledge_transfer", rankdir="LR")
    g.attr(label="Figure 3.14: Knowledge Transfer Spectrum", labelloc="b",
           fontsize=FONT_SIZE_TITLE, fontname=FONT_BOLD,
           nodesep="0.4", ranksep="1.2")

    levels = [
        ("w", "Weight-Level\nDistillation\n\nHinton et al. 2015\nSoft targets, KD loss",
         "#F8D7DA", "Modifies\nweights"),
        ("o", "Output-Level\nDistillation\n\nAlpaca, Vicuna\nGenerated training data",
         "#FCF3CF", "Generates data\nfor fine-tuning"),
        ("p", "Prompt-Level\nTransfer\n\nSPoT, GEPA\nPrompt optimization",
         "#D6EAF8", "Modifies prompt\ntext only"),
        ("t", "This Work\n\nPrompt + Schema\n+ Preprocessor patching",
         "#D5F5E3", "Modifies prompt,\ntool schemas,\n& guardrail code"),
    ]

    prev = None
    for nid, label, color, mechanism in levels:
        g.node(nid, label=label, shape="box", style="filled,rounded",
               fillcolor=color, width="2.5", height="1.6")
        g.node(f"{nid}_m", label=mechanism, shape="box",
               style="filled,rounded", fillcolor="#F8F9FA",
               fontsize=FONT_SIZE_SMALL, fontcolor=GREY,
               color="#DDDDDD", penwidth="0.8")
        g.edge(nid, f"{nid}_m", style="dotted", arrowhead="none", color="#CCCCCC")
        if prev:
            g.edge(prev, nid, label="  lighter  ", fontcolor=GREY,
                   color=GREY, style="dashed", arrowhead="vee")
        prev = nid

    # Highlight "this work"
    g.node("t", penwidth="2.5", color=GREEN)

    # Direction labels
    g.node("heavy", label="Heavier\nintervention", shape="plaintext",
           fontsize=FONT_SIZE_SMALL, fontcolor=GREY, fontname=FONT,
           style="")
    g.node("light", label="Lighter\nintervention", shape="plaintext",
           fontsize=FONT_SIZE_SMALL, fontcolor=GREY, fontname=FONT,
           style="")

    with g.subgraph() as s:
        s.attr(rank="min")
        s.node("heavy")
        s.node("w")
    with g.subgraph() as s:
        s.attr(rank="max")
        s.node("light")
        s.node("t")

    render(g)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ALL_FIGURES = [
    fig_01_outer_loop,
    fig_02_inner_loop,
    fig_03_system_architecture,
    fig_04_teacher_session,
    fig_05_three_conditions,
    fig_06_patch_surfaces,
    fig_07_conversation_mechanics,
    fig_08_failure_taxonomy,
    fig_09_reward_breakdown,
    fig_10_escalation,
    fig_11_parallel_architecture,
    fig_12_patch_pipeline,
    fig_13_gap_closure,
    fig_14_knowledge_transfer,
]


if __name__ == "__main__":
    import sys

    targets = sys.argv[1:] if len(sys.argv) > 1 else []

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
        print(f"Generating {len(ALL_FIGURES)} figures...")
        for fn in ALL_FIGURES:
            print(f"  {fn.__name__}...")
            fn()
        print("Done!")
