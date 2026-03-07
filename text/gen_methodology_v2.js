const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, LevelFormat, PageBreak
} = require('docx');

// ── helpers ──────────────────────────────────────────────────────
const F = 'Times New Roman', S = 24;

function bodyPara(parts, extra = {}) {
  return new Paragraph({
    spacing: { after: 120, line: 360 },
    alignment: AlignmentType.JUSTIFIED,
    ...extra,
    children: parts.map(p =>
      typeof p === 'string'
        ? new TextRun({ text: p, font: F, size: S })
        : new TextRun({ font: F, size: S, ...p })
    )
  });
}
const B = t => ({ text: t, bold: true });
const I = t => ({ text: t, italics: true });
const BI = t => ({ text: t, bold: true, italics: true });
const SUP = t => ({ text: t, superScript: true });

function heading(level, text) {
  return new Paragraph({
    heading: level,
    children: [new TextRun({ text, font: F })],
    spacing: {
      before: level === HeadingLevel.HEADING_1 ? 360 : level === HeadingLevel.HEADING_2 ? 280 : 240,
      after: level === HeadingLevel.HEADING_1 ? 200 : 120
    }
  });
}

const thin = { style: BorderStyle.SINGLE, size: 1, color: '999999' };
const bdr = { top: thin, bottom: thin, left: thin, right: thin };
function tc(text, w, hdr = false) {
  return new TableCell({
    borders: bdr, width: { size: w, type: WidthType.DXA },
    shading: hdr ? { fill: 'E8E8E8', type: ShadingType.CLEAR } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text, font: F, size: 22, bold: hdr })] })]
  });
}
function caption(text) {
  return bodyPara([BI('Table. '), I(text)], { alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 } });
}

const children = [

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_1, '3. Methodology'),

bodyPara([
  'This chapter describes the research design, experimental setup, and implementation of the prompt evolution framework evaluated in this thesis. Section 3.1 situates the research within a design-science paradigm; Section 3.2 describes the evaluation benchmark; Section 3.3 defines the three experimental conditions; Section 3.4 justifies model choices; Sections 3.5\u20133.7 detail the evolution framework, its patch mechanisms, and the failure taxonomy; Section 3.8 defines evaluation metrics; Section 3.9 documents reproducibility provisions; and Section 3.10 discusses threats to validity.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.1 Research Design'),

bodyPara([
  'The research follows a design-science approach (Hevner, March, Park, & Ram, 2004; Peffers, Tuunanen, Rothenberger, & Chatterjee, 2007): the primary contribution is a software artifact\u2014the prompt evolution framework\u2014and the primary evaluation is an empirical measurement of its effect on a standardized benchmark. The study is quantitative and experimental, with a pre-test/post-test design in which the same agent is evaluated before and after the intervention (automated prompt and tool-schema evolution), with an additional ceiling condition provided by a stronger model. Hevner et al.\u2019s Design Evaluation guideline requires demonstrating that the artifact improves upon a baseline and contextualizing improvement against an upper bound; the three-condition design satisfies both requirements.'
]),

bodyPara([
  'The research question\u2014',
  I('How can AI agent performance on structured benchmarks be improved through automated, teacher-model-driven prompt and tool evolution?'),
  '\u2014is operationalized as a measurable change in pass rate on the \u03C4\u00B2-bench benchmark across three experimental conditions. The sub-questions map to specific analyses: failure-mode responsiveness is assessed through the failure taxonomy and ablation of patch types; the efficiency question is addressed by the iterative structure of the loop, which tracks marginal gains per iteration; and the comparison with static agents is enabled by the floor\u2013intervention\u2013ceiling design.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.2 Benchmark: \u03C4\u00B2-bench'),
heading(HeadingLevel.HEADING_3, '3.2.1 Selection Rationale'),

bodyPara([
  'The evaluation benchmark is \u03C4\u00B2-bench (Barres, Dong, Ray, Si, & Narasimhan, 2025), an extension of \u03C4-bench (Yao, Shinn, Razavi, & Narasimhan, 2024). It was selected over four alternative benchmarks for reasons that reduce to a single requirement: the benchmark must combine multi-turn dialogue with tool calling, a simulated user that reveals information incrementally, and domain-specific policy constraints\u2014what makes customer-service automation realistic in practice.'
]),

bodyPara([
  'AgentBench (Liu et al., 2023) covers eight interactive environments but features no simulated user interaction; the agent operates autonomously given all information upfront. SWE-bench (Jimenez, Yang, Wettig, Yao, Pei, Press, & Narasimhan, 2024) is confined to single-shot code generation with no dialogue or tool-calling APIs. GAIA (Mialon, Fourrier, Swift, Wolf, LeCun, & Scialom, 2023) evaluates single-turn factual question answering with no conversational back-and-forth. ToolBench (Qin et al., 2023) tests tool use across 16,000+ APIs, but\u2014as noted in the \u03C4-bench paper\u2014instructions are provided upfront in their entirety: there is no multi-turn user dialogue, no domain policies, and no customer-service workflows. \u03C4\u00B2-bench is the only benchmark that combines all four elements: multi-turn conversations with an LLM-simulated user providing partial information, domain-specific policies, tool-calling APIs that modify database state, and the pass',
  SUP('k'),
  ' reliability metric that the thesis requires.'
]),

heading(HeadingLevel.HEADING_3, '3.2.2 Domains and Tasks'),

bodyPara([
  '\u03C4\u00B2-bench provides three customer-service domains, each with its own database, policy document, tool set, and task catalog.'
]),

new Table({
  width: { size: 9360, type: WidthType.DXA }, columnWidths: [1800, 1800, 5760],
  rows: [
    new TableRow({ children: [tc('Domain',1800,true), tc('Tasks',1800,true), tc('Description',5760,true)] }),
    new TableRow({ children: [tc('Airline',1800), tc('50',1800), tc('Flight reservations, cancellations, upgrades, baggage',5760)] }),
    new TableRow({ children: [tc('Retail',1800), tc('114',1800), tc('Order management, returns, exchanges, account issues',5760)] }),
    new TableRow({ children: [tc('Telecom',1800), tc('114',1800), tc('Mobile plans, data issues, billing, service changes',5760)] }),
  ]
}),
caption('\u03C4\u00B2-bench domain characteristics.'),

bodyPara([
  'Each task defines a user scenario (visible only to the simulated customer), expected agent actions with specific tool calls and arguments, post-conversation database state assertions, and natural-language assertions about the conversation. A task passes if and only if the agent satisfies all criteria simultaneously\u2014the strict binary pass',
  SUP('1'),
  ' metric standard in \u03C4-bench publications. Rabanser, Kapoor, Kirgis, Liu, Utpala, and Narayanan (2026) note that 24 of the original 50 airline tasks contain ground-truth errors; where practical, this thesis uses verified task subsets for the airline domain.'
]),

heading(HeadingLevel.HEADING_3, '3.2.3 Conversation Mechanics'),

bodyPara([
  'During evaluation, a simulated orchestrator manages a turn-by-turn conversation between the agent and a user simulator. On each turn the agent may either send a text message or invoke a tool; it cannot do both. Tool calls are executed against a simulated database, and the result is returned. The conversation ends when the user simulator signals completion or a maximum step count is reached. Each completed conversation is evaluated against the task\u2019s criteria, producing a reward between 0.0 and 1.0. The full trace\u2014user messages, agent messages, tool calls, tool results\u2014is preserved for analysis by the teacher model.'
]),

heading(HeadingLevel.HEADING_3, '3.2.4 Integration'),

bodyPara([
  '\u03C4\u00B2-bench is integrated as a git submodule pinned to commit 37bfc31 (based on tag v0.1.1), installed as an editable Python package. No modifications were made to the upstream codebase; all integration occurs through \u03C4\u00B2-bench\u2019s public API: the RunConfig data model, the run_domain() function, the agent registry, and the Tool and Environment classes. Because nothing in the upstream code was changed, benchmark results are directly comparable to published baselines.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.3 Experimental Conditions'),

bodyPara([
  'The experiment evaluates three conditions across the three \u03C4\u00B2-bench domains. Each uses identical evaluation infrastructure, and they differ only in the agent\u2019s model and prompt configuration. As recommended by Wornow et al. (2024), the design brackets the intervention between a floor (unoptimized student) and a ceiling (frontier model).'
]),

heading(HeadingLevel.HEADING_3, '3.3.1 Condition B: Baseline'),

bodyPara([
  'The student model runs on \u03C4\u00B2-bench tasks with no modifications. The system prompt is \u03C4\u00B2-bench\u2019s default instruction template, which directs the agent to follow the domain policy and produce valid JSON. Tool schemas are the originals. This establishes the performance floor\u2014how well the student performs out of the box.'
]),

heading(HeadingLevel.HEADING_3, '3.3.2 Condition K: Evolved'),

bodyPara([
  'The student model runs with an evolved prompt and tool configuration produced by the evolution framework (Sections 3.5\u20133.6). The evolved state comprises three components: (1) a modified system prompt containing the original plus additions produced by the teacher\u2019s patch_prompt calls\u2014typically concrete behavioral rules such as identity verification requirements or tool-call sequencing instructions; (2) modified tool schemas with clarified parameter descriptions, added constraints, or edge-case notes; and (3) tool preprocessors\u2014sandboxed Python functions that transform tool inputs before execution, that guard against common LLM formatting errors.'
]),

heading(HeadingLevel.HEADING_3, '3.3.3 Condition F: Frontier Ceiling'),

bodyPara([
  'The teacher model (Kimi K2.5) runs as the agent directly, using the default, unmodified \u03C4\u00B2-bench prompt and tools. This measures the upper bound\u2014how well the strongest available model performs without any evolution\u2014and provides a normalization denominator for the gap-closure metric (Section 3.8).'
]),

heading(HeadingLevel.HEADING_3, '3.3.4 Three-Way Comparison Logic'),

bodyPara([
  'The three conditions form a floor\u2013intervention\u2013ceiling comparison analogous to teacher\u2013student distillation studies, where a teacher\u2019s performance defines the ceiling, a student\u2019s pre-distillation performance defines the floor, and the post-distillation student occupies the intervention position (Hinton, Vinyals, & Dean, 2015). The difference is that knowledge transfer operates at the prompt level, not the weight level. The baseline alone is uninterpretable: a pass rate of 60 percent means nothing without context. The frontier provides that context. If it achieves 90 percent, the gap is 30 percentage points, and the evolved condition\u2019s position within that gap indicates how much of the teacher\u2019s advantage was transferred through prompt engineering alone, with no weight changes.'
]),

heading(HeadingLevel.HEADING_3, '3.3.5 Per-Domain Independence'),

bodyPara([
  'Each domain is evolved independently. There is no cross-domain transfer of patches. A rule learned from airline cancellation failures (\u201calways check refund eligibility before cancelling\u201d) is irrelevant in the telecom domain. The evolution loop runs separately per domain, producing domain-specific evolved prompts. This also allows per-domain analysis of which failure types respond to the intervention.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.4 Model Selection and Justification'),

bodyPara([
  'All models are accessed through OpenRouter using a single API key.'
]),

new Table({
  width: { size: 9360, type: WidthType.DXA }, columnWidths: [2000, 3680, 3680],
  rows: [
    new TableRow({ children: [tc('Role',2000,true), tc('Model',3680,true), tc('Access Method',3680,true)] }),
    new TableRow({ children: [tc('Student agent',2000), tc('Qwen3 30B-A3B',3680), tc('litellm via \u03C4\u00B2-bench',3680)] }),
    new TableRow({ children: [tc('User simulator',2000), tc('Qwen3 30B-A3B',3680), tc('litellm via \u03C4\u00B2-bench',3680)] }),
    new TableRow({ children: [tc('Teacher',2000), tc('Kimi K2.5',3680), tc('OpenAI client direct',3680)] }),
  ]
}),
caption('Model assignments and access methods.'),

heading(HeadingLevel.HEADING_3, '3.4.1 Student Model: Qwen3 30B-A3B'),

bodyPara([
  'The student model is Qwen3 30B-A3B (Qwen Team, 2025), a Mixture-of-Experts Transformer with 30.5 billion total parameters but only 3.3 billion active per token. It employs 128 experts with top-8 routing across 48 layers and supports 32,768 native context tokens extensible to 131,072 with YaRN scaling. Despite activating barely 10 percent of its parameters per forward pass, the model outperforms Qwen2.5-14B on all reported benchmarks and leads the Berkeley Function Calling Leaderboard (BFCL v3). The selection reflects a trade-off: the model needs non-trivial \u03C4\u00B2-bench scores, but must be weak enough relative to the frontier that meaningful headroom exists, and cheap enough for the many evaluation runs the iterative process requires. Qwen3 30B-A3B fits: its MoE architecture makes it fast and inexpensive via API, it handles tool-calling and multi-turn dialogue, and it is demonstrably imperfect on \u03C4\u00B2-bench tasks.'
]),

bodyPara([
  'Alternative student models\u2014Qwen3.5 Flash and GLM 4.7 Flash\u2014are supported by the implementation for cross-student ablation, but the primary evaluation uses Qwen3 30B-A3B.'
]),

heading(HeadingLevel.HEADING_3, '3.4.2 Teacher Model: Kimi K2.5'),

bodyPara([
  'The teacher model is Kimi K2.5 (Kimi Team, 2026), a visual-agentic extension of the Kimi K2 base model (Kimi Team, 2025). The base model is a MoE Transformer with approximately one trillion total parameters and 32 billion active per token, employing 384 experts\u201450 percent more than DeepSeek-V3\u2014with Multi-head Latent Attention. Its 256K-token context window accommodates full conversation traces (often 5\u201315 turns with tool calls and results), the system prompt, all tool schemas, and task requirements in a single prompt. The teacher was chosen for significantly stronger performance than the student on target domains, strong tool-calling comprehension, a long context window, architectural independence from the student (Moonshot AI, not Alibaba), and cost-effectiveness for hundreds of reflection calls.'
]),

bodyPara([
  'Using a separate, stronger model to diagnose and correct the student\u2019s failures draws on knowledge distillation (Hinton et al., 2015) and more recent teacher\u2013student paradigms, including adversarial distillation (Jiang, Chan, Chen, & Wang, 2023) and the LLM-as-judge approach. Zheng et al. (2023) established that GPT-4 agrees with human preferences over 80 percent of the time; subsequent work has tightened this estimate. Zhuge et al. (2024) showed that an agent-based judge achieves approximately 90 percent agreement with human experts in agentic evaluation settings, while Gilardi, Alizadeh, and Kubli (2023) found that ChatGPT outperforms crowd-workers by 25 percentage points on annotation tasks with intercoder agreement of 91\u201397 percent. These results support using a frontier model as a diagnostic supervisor. Here, though, knowledge transfer happens through prompt and tool-schema patches only\u2014no training data, no weight updates. This is a lighter mechanism, consistent with the Superficial Alignment Hypothesis (Zhou et al., 2023): if alignment mostly teaches style and format, prompt text should suffice.'
]),

heading(HeadingLevel.HEADING_3, '3.4.3 User Simulator'),

bodyPara([
  'The user simulator uses the same model as the student (Qwen3 30B-A3B). \u03C4\u00B2-bench\u2019s user simulator follows scripted scenarios; it does not require frontier-level capabilities. Using the same inexpensive model keeps costs low without affecting evaluation validity.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.5 The Evolution Framework'),
heading(HeadingLevel.HEADING_3, '3.5.1 Architecture Overview'),

bodyPara([
  'The evolution framework implements a diagnose-patch-validate loop. A weaker student model runs on benchmark tasks and fails on some. A stronger teacher model analyzes each failure, proposes modifications to the student\u2019s prompt and tool configuration, and those modifications are validated by re-running the student on the failed task. Successful patches are merged into a progressively improved agent configuration. The architecture operates at two levels: an outer loop iterates over the full task set, and an inner loop handles individual failure repair.'
]),

bodyPara([
  'In the automated prompt optimization literature, this is a teacher-driven variant of reflective prompt evolution. The closest precedent is GEPA (Agrawal et al., 2025), a Genetic-Pareto prompt optimizer accepted as an oral at ICLR 2026, which uses natural language reflection from a stronger model to diagnose failures from execution traces and propose targeted mutations for a weaker task model, outperforming reinforcement learning baselines by up to 20 percent while using 35\u00D7 fewer rollouts. The present framework shares GEPA\u2019s core mechanism\u2014a strong reflection model inspecting the weaker model\u2019s failures and proposing prompt edits\u2014but departs from it in three respects. First, the patches target prompt text, tool schemas, and sandboxed input preprocessors\u2014three distinct surfaces. Second, every proposed patch is validated by re-running the student on the specific failed task before merging, so only verified improvements enter the production prompt. Third, the evaluation target is a structured tool-agent-user benchmark (\u03C4\u00B2-bench) instead of reasoning or classification tasks. As noted in the literature review, automated prompt optimization methods have not been tested on multi-turn tool-calling benchmarks.'
]),

bodyPara([
  'DSPy (Khattab et al., 2023) compiles declarative modules against a target metric through self-bootstrapping; TextGrad (Yuksekgonul et al., 2024) backpropagates textual feedback through computation graphs. The present framework does neither\u2014it uses a separate teacher model to perform structured diagnosis and targeted patching on a per-failure basis. In Reflexion (Shinn, Cassano, Gopinath, Narasimhan, & Yao, 2023), reflections are ephemeral per-episode memory; here, patches are permanent modifications persisted across episodes and iterations.'
]),

heading(HeadingLevel.HEADING_3, '3.5.2 The Outer Loop'),

bodyPara([
  'The outer loop proceeds as follows for each iteration. First, the student is evaluated on all benchmark tasks (excluding previously dropped tasks) with the current evolved state, and results are saved. Second, tasks with reward strictly less than 1.0 are extracted as failures. Third, for each failed task, a teacher session is spawned in parallel to diagnose the failure and propose patches; each patch set is validated by re-running the student on that task. Fourth, all accepted patches are merged into the global state. Fifth, all attempted tasks\u2014both fixed and unfixed\u2014are dropped from future evaluation. The loop repeats until no failures remain, all tasks have been dropped, or the maximum iteration count is reached.'
]),

bodyPara([
  'Dropping both fixed and unfixed tasks is deliberate. Fixed tasks were already validated during the fix phase; re-evaluating them wastes API budget. Unfixed tasks could not be repaired within the allotted retries; re-attempting with a marginally different global prompt is unlikely to succeed and risks conflicting patches. These tasks are treated as intractable for the current teacher\u2013student pair.'
]),

heading(HeadingLevel.HEADING_3, '3.5.3 The Inner Loop: Per-Failure Fix Attempts'),

bodyPara([
  'For each failed task, a teacher session is created with deep copies of the current global state. The session enters a reflect-validate loop with up to 1 + ',
  I('max_retries'),
  ' attempts. In the reflection step, the teacher receives a comprehensive prompt containing the agent\u2019s current system prompt, all tool schemas, the full failed conversation trace, the task requirements, and the reward breakdown. It diagnoses the root cause, classifies it (Section 3.7), and calls patch tools to propose modifications. In the validation step, the student is re-run on the same task with the patches applied. If the patched reward exceeds the baseline reward, the fix is accepted. If not, the teacher receives the new conversation trace, the new reward breakdown, and the current state of all its modifications, and is asked to try again.'
]),

bodyPara([
  'Patches are merged into the global state only if validation succeeds. Failed patches are discarded entirely. The fix success criterion is permissive: any improvement in reward counts, not just reaching a perfect 1.0. A patch improving a task\u2019s reward from 0.0 to 0.5 is accepted and merged, potentially enabling further improvement in subsequent iterations.'
]),

heading(HeadingLevel.HEADING_3, '3.5.4 The Teacher Session'),

bodyPara([
  'The teacher session maintains a stateful conversation with the teacher model using function calling. The teacher has access to four tools: ',
  B('patch_prompt'),
  ' (find-and-replace on the system prompt), ',
  B('patch_tool'),
  ' (find-and-replace on a tool\u2019s JSON schema), ',
  B('read_tool_code'),
  ' (inspect a tool\u2019s parameters and current preprocessor), and ',
  B('patch_tool_code'),
  ' (find-and-replace on a tool\u2019s preprocessor source). The initial prompt is a structured template containing five sections: the current system prompt, all tool schemas serialized to JSON, the full failed conversation trace with role labels and preserved tool-call arguments, the task requirements, and the reward breakdown. Automated tests verify that no data is lost or truncated during formatting, since the teacher cannot diagnose what it cannot see. The teacher may make up to 10 rounds of tool calls per session; in practice, most sessions complete in two to four rounds.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.6 Patch Surfaces and Mechanisms'),

bodyPara([
  'The framework operates on three distinct patch surfaces, each for a different class of agent failure. All patches use a find-and-replace mechanism: the teacher specifies an old_text to locate and a new_text to substitute, which keeps modifications precise, minimal, and reversible.'
]),

heading(HeadingLevel.HEADING_3, '3.6.1 Prompt Patches'),

bodyPara([
  'Prompt patches modify the agent\u2019s system prompt, typically adding concrete behavioral rules the student was not following. When old_text is empty, new_text is appended to the prompt\u2019s end. Instead of fine-tuning weights to encode a behavioral rule, the rule is simply stated in natural language within the prompt. The Superficial Alignment Hypothesis (Zhou et al., 2023) suggests this should work: alignment primarily teaches style and format, which prompt text can supply. Sclar, Choi, Tsvetkov, and Suhr (2024) demonstrated up to 76 accuracy points of variation from meaning-preserving formatting changes alone (spacing, delimiters, example ordering), a sensitivity that persisted even with increased model size or instruction tuning. The patches in this framework are meaning-bearing\u2014rewriting instructions, adding policy constraints\u2014not formatting noise. Sclar et al. show that arbitrary formatting changes cause chaotic performance swings; the question here is whether deliberate, diagnostic-driven edits behave differently.'
]),

heading(HeadingLevel.HEADING_3, '3.6.2 Tool Schema Patches'),

bodyPara([
  'Tool schema patches modify the JSON schemas that define how the agent calls each tool. These schemas are presented as part of the function-calling interface and directly affect tool selection, argument formatting, and constraint adherence. Common modifications include clarifying parameter descriptions (adding \u201cmust start with #\u201d to a reservation_id field), expanding tool descriptions to note when a tool should or should not be used, and adding constraint notes. After each edit, the JSON string is parsed to ensure syntactic validity; patches producing invalid JSON are rejected.'
]),

bodyPara([
  'Parameter and formatting errors in tool calling are well studied. Qin et al. (2023) showed that without their depth-first search approach, an initial parameter error \u201ccan lead to a cascade of subsequent errors\u201d that trap the model in a faulty loop of incorrect API calls. Xu, Hong, Li, Hu, Chen, and Zhang (2023) found that generation style regulation\u2014fixing formatting and parameter errors\u2014was effective, with targeted constraints boosting open-source LLMs to competitive with GPT-4 on 4 of 8 tasks. StableToolBench (Guo et al., 2024) found that up to 50 percent of queries and 75 percent of trajectories in the original ToolBench data suffered from hallucinations, meaning parameter extraction errors are systemic, not incidental.'
]),

heading(HeadingLevel.HEADING_3, '3.6.3 Tool Preprocessors'),

bodyPara([
  'Tool preprocessors are sandboxed Python functions that transform tool-call arguments before execution. Every tool starts with an identity preprocessor. The teacher can modify the code to add defensive input coercion\u2014ensuring an ID field has the correct prefix, casting strings to integers, normalizing date formats. Preprocessors are sandboxed: a static analysis pass rejects forbidden constructs (imports, eval, exec, file I/O), the execution namespace restricts available builtins, and runtime exceptions fall back to the original arguments.'
]),

bodyPara([
  'Some formatting errors persist even when the prompt and schema are clear: the model understands the requirement but still gets it wrong. An agent may understand that reservation IDs should start with \u201c#\u201d but occasionally omit the prefix due to tokenization or sampling artifacts. A preprocessor guardrail catches such errors at the tool-call boundary. The design parallels findings from the ARTEMIS framework (Brookes et al., 2025), which jointly optimizes agent prompts, tool descriptions, and parameters using evolutionary methods, reporting 13.6 percent improvement on competitive programming and 22 percent on GSM8K for Qwen2.5-7B.'
]),

heading(HeadingLevel.HEADING_3, '3.6.4 Patch Application and Merging'),

bodyPara([
  'Patches are applied sequentially using first-occurrence-only string replacement to prevent cascading substitutions. Failed patches (old_text not found) are logged and skipped without aborting the batch. When multiple tasks are fixed in a single iteration, winning patches are merged into the global state in sequence. The evolved state is serialized to disk as a JSON file containing the full prompt, all tool schemas, and all preprocessor source code, so the exact evolved agent can be reconstructed at any point.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.7 Failure Taxonomy'),

bodyPara([
  'The teacher classifies each failure into one of four categories as part of its diagnostic output.'
]),

new Table({
  width: { size: 9360, type: WidthType.DXA }, columnWidths: [2200, 3580, 3580],
  rows: [
    new TableRow({ children: [tc('Category',2200,true), tc('Description',3580,true), tc('Examples',3580,true)] }),
    new TableRow({ children: [tc('TOOL_MISUSE',2200), tc('Wrong tool, wrong parameters, missing tool call',3580), tc('Using get_flight_details instead of get_reservation_details',3580)] }),
    new TableRow({ children: [tc('POLICY_VIOLATION',2200), tc('Skipped validation step or broke a constraint',3580), tc('Cancelling without checking refund eligibility',3580)] }),
    new TableRow({ children: [tc('REASONING_ERROR',2200), tc('Incorrect assumption, incomplete plan',3580), tc('Assuming a flight is direct when it has connections',3580)] }),
    new TableRow({ children: [tc('COMMUNICATION_ERROR',2200), tc('Confusing message, failed to guide user',3580), tc('Not explaining applicable fees to the customer',3580)] }),
  ]
}),
caption('Failure taxonomy for teacher-model diagnosis.'),

bodyPara([
  'Classification is automated: the teacher includes the failure type in its diagnostic text, and the category is extracted by string matching. This is a heuristic\u2014the teacher might use different phrasing, or a failure might span multiple categories. The implementation takes the first match, defaulting to REASONING_ERROR when none is found. Kapoor, Stroebl, Siegel, Nadgir, and Narayanan (2024) identified similar categorization challenges in their analysis of agent benchmarking practices, noting that benchmark shortcomings can be organized by failure mode (narrow accuracy focus, benchmark overfitting, cost blindness) but that any taxonomy risks oversimplification. A more robust classification mechanism\u2014for example, a structured output field\u2014could improve accuracy in future work.'
]),

bodyPara([
  'The taxonomy enables per-category analysis of which failure types are most responsive to prompt evolution versus tool-schema patching versus preprocessor guardrails, which is what the sub-question about failure-mode responsiveness requires.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.8 Evaluation Metrics'),
heading(HeadingLevel.HEADING_3, '3.8.1 Primary Metric: pass\u00B9'),

bodyPara([
  'The primary metric is pass',
  SUP('1'),
  '\u2014the fraction of tasks achieving a perfect reward of 1.0. This is the standard metric in \u03C4-bench publications (Yao et al., 2024; Barres et al., 2025). Any reward below 1.0 constitutes failure. The strictness is intentional: Rabanser et al. (2026) argue that enterprise autonomous operation requires three to five nines of reliability (99.9\u201399.999 percent) and that current LLM agents are not on track to reach this threshold through scaling alone, with accuracy improving faster than reliability across 14 models spanning 18 months of releases. Under such a standard, partial credit is meaningless.'
]),

heading(HeadingLevel.HEADING_3, '3.8.2 Reward Breakdown'),

bodyPara([
  '\u03C4\u00B2-bench\u2019s evaluator produces a multi-dimensional reward: an action score (correct tools with correct arguments), environment assertions (expected database state), and a communication score (correct user-facing messages). This breakdown is passed in full to the teacher during diagnosis so it can identify exactly which criteria failed and why.'
]),

heading(HeadingLevel.HEADING_3, '3.8.3 Gap Closure'),

bodyPara([
  'To normalize for domain difficulty, gap closure is computed as: (K \u2212 B) / (F \u2212 B) \u00D7 100%, where K is the evolved pass rate, B the baseline, and F the frontier. A gap closure of 50 percent means the evolved prompt captured half the teacher\u2019s advantage through prompt and tool-schema patching alone. The metric is defined only when F > B.'
]),

heading(HeadingLevel.HEADING_3, '3.8.4 Fix Success Rate'),

bodyPara([
  'A fix succeeds when the patched reward strictly exceeds the baseline reward. The fix success rate\u2014the fraction of attempted fixes that succeed\u2014measures the evolution process\u2019s efficiency.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.9 Reproducibility'),
heading(HeadingLevel.HEADING_3, '3.9.1 Fixed Parameters'),

new Table({
  width: { size: 9360, type: WidthType.DXA }, columnWidths: [2800, 1600, 4960],
  rows: [
    new TableRow({ children: [tc('Parameter',2800,true), tc('Value',1600,true), tc('Rationale',4960,true)] }),
    new TableRow({ children: [tc('Random seed',2800), tc('42',1600), tc('Deterministic task selection and ordering',4960)] }),
    new TableRow({ children: [tc('Trials per task',2800), tc('1',1600), tc('Single trial per evaluation',4960)] }),
    new TableRow({ children: [tc('Teacher temperature',2800), tc('0.3',1600), tc('Focused diagnostic output',4960)] }),
    new TableRow({ children: [tc('Reasoning suppression',2800), tc('Enabled',1600), tc('Prevents reasoning tokens from breaking content parsing',4960)] }),
    new TableRow({ children: [tc('Max teacher rounds',2800), tc('10',1600), tc('Multi-step diagnosis without unbounded cost',4960)] }),
  ]
}),
caption('Fixed experimental parameters.'),

heading(HeadingLevel.HEADING_3, '3.9.2 Software Environment'),

bodyPara([
  'The implementation uses Python 3.12 with \u03C4\u00B2-bench at commit 37bfc31, the uv build system with hatchling backend, litellm for LLM routing, and the OpenAI Python SDK (\u22651.0) for teacher calls. All models are accessed through OpenRouter. The source code is publicly available at github.com/glebdementev/tau-evo.'
]),

heading(HeadingLevel.HEADING_3, '3.9.3 State Persistence and Task Locking'),

bodyPara([
  'The complete evolution state is serialized to JSON after each iteration: the current system prompt, all tool schemas, all preprocessor source, iteration history with fix results, and metadata. Loading this state reconstructs the exact evolved agent. After the first evaluation in a run, task IDs are locked and reused for all subsequent iterations, so pass-rate changes reflect patches, not sampling variation.'
]),

// ═══════════════════════════════════════════════════════════════════
heading(HeadingLevel.HEADING_2, '3.10 Threats to Validity'),
heading(HeadingLevel.HEADING_3, '3.10.1 Internal Validity'),

bodyPara([
  B('Single trial per task. '),
  'Each task is evaluated once per iteration, introducing variance from stochastic LLM generation. Yao et al. (2024) introduced the pass',
  SUP('k'),
  ' metric precisely to capture this variance, showing that pass',
  SUP('8'),
  ' can drop below 25 percent even when pass',
  SUP('1'),
  ' exceeds 50 percent. The limitation is mitigated by the fixed seed and by reporting results across multiple tasks, but full confidence intervals would require multiple trials per task at additional cost.'
]),

bodyPara([
  B('Teacher model bias. '),
  'The teacher\u2019s diagnoses and patches reflect the capabilities and blind spots of Kimi K2.5. A different teacher might produce different patches and improvement trajectories. The mitigation is empirical validation: only patches that demonstrably improve the student\u2019s performance enter the global state. Dorner, Nastl, et al. (2024) showed that when the judge is no more capable than the evaluated model, debiasing cannot fully compensate; this limitation does not apply here, since Kimi K2.5 is substantially stronger than Qwen3 30B-A3B.'
]),

bodyPara([
  B('Heuristic failure classification. '),
  'The four-category taxonomy is applied through string matching on the teacher\u2019s free-text diagnosis. Misclassification is possible. This affects per-category analysis but not primary pass-rate results.'
]),

heading(HeadingLevel.HEADING_3, '3.10.2 External Validity'),

bodyPara([
  B('Benchmark versus production. '),
  '\u03C4\u00B2-bench tasks are simulated customer-service interactions. While designed to approximate operational settings, they lack the full diversity and adversarial nature of real interactions. Kapoor et al. (2024) documented that 7 of 8 major agent benchmarks lack appropriate holdout sets and that benchmark-specific overfitting is common\u2014the top WebArena agent hardcodes policies for specific tasks. Whether the framework works in production is untested.'
]),

bodyPara([
  B('Model generalization. '),
  'The framework is evaluated with one student\u2013teacher pair. Whether results generalize to stronger students (where headroom is smaller) or weaker teachers (where diagnostic quality degrades) is an open question. Alternative student models are supported for future ablation.'
]),

bodyPara([
  B('Domain specificity. '),
  'Patches are domain-specific by design. The framework does not claim cross-domain transfer; the claim is that domain-specific diagnostic knowledge can be transferred efficiently to a weaker model\u2019s prompt configuration.'
]),

heading(HeadingLevel.HEADING_3, '3.10.3 Construct Validity'),

bodyPara([
  B('pass\u00B9 as reliability proxy. '),
  'The metric treats all failures equally\u2014a catastrophic wrong action and a minor communication lapse both count. Rabanser et al. (2026) decompose reliability into four dimensions (consistency, robustness, predictability, safety) with twelve metrics, of which pass',
  SUP('1'),
  ' captures only the consistency dimension. The reward breakdown provides more granular information, but the primary metric does not weight by severity or dimension.'
]),

bodyPara([
  B('Prompt evolution as distillation. '),
  'The thesis frames prompt patching as a form of knowledge transfer from teacher to student. There is precedent: weight-level distillation (Hinton et al., 2015), output-level distillation (Alpaca, Vicuna), and prompt-level transfer (SPoT; Vu, Lester, Constant, Al-Rfou, & Cer, 2022; GEPA; Agrawal et al., 2025) form a progression toward lighter-weight knowledge transfer. However, the patches may encode surface-level heuristics (add a \u201c#\u201d prefix) without transferring deep domain understanding, and their durability under distribution shift is untested.'
]),

];

module.exports = children;
