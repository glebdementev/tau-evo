const {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  AlignmentType, PageBreak, BorderStyle, WidthType, ShadingType
} = require("docx");

// Helper: make a paragraph with mixed runs
function p(runs, opts = {}) {
  return new Paragraph({
    spacing: { after: 200, line: 360 },
    alignment: AlignmentType.JUSTIFIED,
    ...opts,
    children: runs
  });
}

function t(text, opts = {}) {
  return new TextRun({ text, font: "Times New Roman", size: 24, ...opts });
}

function ti(text) {
  return t(text, { italics: true });
}

function tb(text) {
  return t(text, { bold: true });
}

// Section heading
function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 360, after: 240 },
    children: [new TextRun({ text, font: "Times New Roman", size: 32, bold: true })]
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 300, after: 200 },
    children: [new TextRun({ text, font: "Times New Roman", size: 28, bold: true })]
  });
}

const children = [];

// ============================================================
// SECTION 2: LITERATURE REVIEW
// ============================================================

children.push(h1("2. Literature Review"));

// INTRODUCTION
children.push(p([
  t("This chapter surveys the literature across three areas that converge on the research gap this thesis addresses: agentic benchmarking, automated prompt optimization, and teacher\u2013student knowledge transfer. The argument proceeds in six steps. Tool-using LLM agents are unreliable at enterprise scale. Static prompting helps but hits a ceiling. Fine-tuning and RLHF work but are impractical for rapid domain adaptation. Automated prompt optimization is effective yet untested on structured tool-calling benchmarks. Teacher\u2013student distillation is mature at the weight level and growing at the output level. The combination of teacher-driven prompt evolution validated on agentic benchmarks has not been attempted. Section 2.6 synthesizes these observations into the specific gap this thesis fills.")
]));

// ============================================================
// 2.1 THE ENTERPRISE RELIABILITY GAP
// ============================================================

children.push(h2("2.1 The Enterprise Reliability Gap in Tool-Using Agents"));

children.push(p([
  t("Recent benchmarks evaluate LLMs not just as text generators but as autonomous agents that hold multi-turn conversations, call tools, and follow domain policies. The \u03C4-bench family is central to this thesis. Yao, Shinn, Razavi, and Narasimhan (2024) introduced \u03C4-bench, which measures tool\u2013agent\u2013user interaction across retail and airline customer-service domains. Even GPT-4o succeeded on fewer than half of all tasks, and the pass"),
  t("k", { superScript: true }),
  t(" reliability metric\u2014which measures the probability of solving the same task "),
  ti("k"),
  t(" consecutive times\u2014showed that pass"),
  t("8", { superScript: true }),
  t(" dropped below 25% in the retail domain. Barres, Dong, Ray, Si, and Narasimhan (2025) extended this work with \u03C4\u00B2-bench, introducing a dual-control environment where both the agent and a simulated user have access to tools and databases, and adding a telecom domain. The expanded setup exposed further failure modes, particularly in scenarios requiring the user to perform physical actions such as troubleshooting network equipment, and confirmed that frontier models remain far from reliable even in the enriched evaluation setting.")
]));

children.push(p([
  t("Other benchmarks tell the same story. Liu et al. (2023) tested twenty-nine models on AgentBench across eight interactive environments (OS interaction, databases, web browsing) and found a large gap between commercial and open-source models, with long-term reasoning, decision-making, and instruction following as the main bottlenecks. Jimenez, Yang, Wettig, Yao, Pei, Press, and Narasimhan (2024) introduced SWE-bench, 2,294 real-world software engineering tasks from GitHub issues. The best model at publication solved 1.96% of them. Autonomous multi-step tool use remains unreliable even in code, the domain where LLMs are supposed to be strongest.")
]));

children.push(p([
  t("Tool-use-specific benchmarks confirm this. Qin et al. (2023) introduced ToolBench with over 16,000 real-world RESTful APIs; open-source instruction-tuned models scored zero percent, and even ChatGPT needed a novel depth-first search decision tree to perform reasonably. Li et al. (2023) built API-Bank with 73 tools across 314 dialogues and found that GPT-4 still failed at parameter extraction, API selection, and sequential planning. Mialon et al. (2023) presented GAIA, 466 real-world questions requiring reasoning, browsing, and tool use. Humans scored 92%; GPT-4 with plugins scored 15%. That 77-point gap runs opposite to the usual story of LLMs matching or beating human performance on standard benchmarks.")
]));

children.push(p([
  t("Two meta-analyses frame these results. Kapoor, Stroebl, Siegel, Nadgir, and Narayanan (2024) analyzed agent benchmarking practices and found fifty-fold cost variation for similar accuracy levels; complex agent architectures buy marginal accuracy gains at exponential cost. This supports the argument that prompt-level optimization is a more efficient improvement path than architectural scaling. Rabanser, Kapoor, Kirgis, Liu, Utpala, and Narayanan (2025) proposed twelve metrics decomposing agent reliability across consistency, robustness, predictability, and safety. Testing fourteen models over eighteen months on GAIA and \u03C4-bench, they identified a persistent "),
  ti("capability\u2013reliability gap"),
  t(": accuracy improves faster than reliability. They argue that enterprise autonomous operation requires three to five nines (99.9%-99.999%) and that current LLM agents are not on track to reach this threshold through scaling alone.")
]));

// ============================================================
// 2.2 STATIC PROMPTING CEILING
// ============================================================

children.push(h2("2.2 The Ceiling of Static Prompting and Scaffolding"));

children.push(p([
  t("Researchers have tried to improve agent performance through better prompt design and execution scaffolding. Chain-of-thought prompting (Wei et al., 2022) showed that a few hand-crafted reasoning exemplars can substantially improve arithmetic, commonsense, and symbolic reasoning, with PaLM-540B reaching state-of-the-art on GSM8K. The ReAct framework (Yao, Zhao, Yu, Du, Shafran, Narasimhan, & Cao, 2023) interleaved reasoning traces with task-specific actions, letting models call external tools while maintaining reasoning chains. ReAct outperformed both pure chain-of-thought and pure action-generation baselines on question answering, fact verification, and interactive decision-making. Yao, Yu, Zhao, Shafran, Griffiths, Cao, and Narasimhan (2023) generalized this with Tree of Thoughts, where LMs explore multiple reasoning paths via tree search with self-evaluation, reaching 74% on Game of 24 compared to chain-of-thought's 4%.")
]));

children.push(p([
  t("On the tool-use front, OpenAI (2023) introduced function calling, moving interaction from free-form text generation to schema-driven structured output and implicitly conceding that pure natural-language prompting is not enough for reliable tool invocation. Schick et al. (2023) trained Toolformer in a self-supervised manner to invoke external tools autonomously, matching much larger models at zero-shot performance. Patil, Zhang, Wang, and Gonzalez (2023) fine-tuned LLaMA through Gorilla to surpass GPT-4 on API call generation, while also showing that GPT-4 frequently hallucinates incorrect API usage under prompting alone. Willard and Louf (2023) tackled the format reliability problem with constrained decoding via finite-state machines, guaranteeing valid structured output but only addressing format, not reasoning or planning.")
]));

children.push(p([
  t("For all these advances, static approaches share a basic limitation: they fix the agent's behavioral repertoire at design time. ReAct exemplars are hand-crafted and task-specific. Function schemas consume tokens and need careful engineering. Chain-of-thought reasoning only emerges at roughly 100 billion parameters (Wei et al., 2022). Brown et al. (2020) showed that in-context few-shot learning has task-dependent ceilings, with GPT-3 failing on ANLI and QuAC. Zhou, Muresanu, Han, Paster, Pitis, Chan, and Ba (2022) found through Automatic Prompt Engineer (APE) that optimal prompts are fragile: small wording changes alter effectiveness, making prompt engineering look more like program synthesis over a brittle search space.")
]));

children.push(p([
  t("Sclar, Choi, Tsvetkov, and Suhr (2023) provide the sharpest evidence for this ceiling. They showed that meaning-preserving formatting changes in few-shot prompts produce up to 76 accuracy points of variation on LLaMA-2-13B, from changes as trivial as spacing and delimiter choice. Larger models, more examples, and instruction tuning did not eliminate this sensitivity. For agent deployment, the consequence is that static prompt scaffolds, no matter how carefully designed, cannot guarantee consistent behavior. Performance depends on design-time decisions that may be suboptimal or brittle under distribution shift, and there is no built-in mechanism for the agent to adapt when it hits new failure modes in production.")
]));

// ============================================================
// 2.3 RLHF IMPRACTICALITY
// ============================================================

children.push(h2("2.3 The Impracticality of Fine-Tuning for Rapid Enterprise Adaptation"));

children.push(p([
  t("RLHF has been the main approach for aligning language models with human intent. Ouyang et al. (2022) showed with InstructGPT that a 1.3-billion-parameter model trained with human feedback is preferred over 175-billion-parameter GPT-3. But the infrastructure cost is high: labeler-written demonstrations, multi-stage reward modeling, and iterative RL optimization, all requiring extensive human annotation. The authors noted an \"alignment tax\" where alignment degrades performance on public NLP benchmarks. Bai et al. (2022) proposed Constitutional AI (CAI) to reduce the human feedback burden, replacing human harmlessness labels with model-generated critiques guided by constitutional principles. CAI still needs a complex multi-phase pipeline of supervised self-critique followed by reinforcement learning.")
]));

children.push(p([
  t("Later work simplified the pipeline without removing the core constraints. Rafailov, Sharma, Mitchell, Manning, Ermon, and Finn (2023) introduced Direct Preference Optimization (DPO), which eliminates the separate reward model and RL stage by directly optimizing the language model on preference data with a classification loss. DPO matches or exceeds PPO-based RLHF with much less complexity, but the bottleneck remains: collecting or generating domain-specific preference data. Every new company policy or workflow change would require new preference pairs, making DPO no more practical than RLHF for rapid enterprise adaptation. Hu, Shen, Wallis, Allen-Zhu, Li, Wang, Wang, and Chen (2022) reduced fine-tuning costs through LoRA, which injects trainable low-rank matrices while freezing pretrained weights, cutting trainable parameters by up to 10,000x. LoRA makes fine-tuning cheaper but does not eliminate the need for task-specific training data or the risk of catastrophic forgetting.")
]));

children.push(p([
  t("The limitations are well-documented. Casper et al. (2023) surveyed RLHF challenges, including noisy and biased human feedback, reward hacking, distributional shift, instability, and sycophancy, arguing that RLHF is not a complete alignment framework and that human evaluators miss over half of critical errors. Lin et al. (2024) quantified the alignment tax directly: RLHF degrades pretrained abilities in translation, reading comprehension, and common-sense reasoning, and existing mitigations (LoRA, regularization) do not fully compensate. Luo, Yang, Meng, Li, and Zhou (2023) confirmed that catastrophic forgetting during continual fine-tuning affects all model sizes and, counterintuitively, that larger models forget more. Fine-tuning for one enterprise task (say, compliance checking) risks degrading performance on another (say, customer support).")
]));

children.push(p([
  t("Zhou, Liu, Xu, Iyer, Sun, Mao, Ma, Efrat, Yu, Yu, Zhang, Ghosh, Lewis, Zettlemoyer, and Levy (2023) offered a different angle with LIMA, showing that fine-tuning on just 1,000 carefully curated examples can produce strong alignment. Their \"Superficial Alignment Hypothesis\" holds that alignment primarily teaches style and format rather than injecting knowledge, which aligns with this thesis's premise that prompt-level interventions can produce real behavioral changes. But LIMA depends on painstaking manual curation, and each new enterprise domain would need its own expert-curated dataset. Across the board, fine-tuning approaches impose costs in data collection, compute, and maintenance that make them unsuitable for the rapid, reversible, domain-specific agent improvement that enterprises need.")
]));

// ============================================================
// 2.4 AUTOMATED PROMPT OPTIMIZATION
// ============================================================

children.push(h2("2.4 Automated Prompt Optimization: Power Without Agentic Validation"));

children.push(p([
  t("Prompts can be optimized automatically, without updating model weights. This section reviews the main approaches and identifies a blind spot they all share: none have been validated on structured tool-agent-user benchmarks.")
]));

children.push(p([
  t("Khattab et al. (2023) introduced DSPy, a framework that abstracts language model pipelines as declarative modules with learnable parameters\u2014prompts and demonstrations\u2014and provides a compiler that automatically optimizes pipelines against a target metric. GPT-3.5 and Llama2-13b self-bootstrap pipelines that outperform expert-created demonstrations by 5\u201346% on multi-hop QA and math reasoning. Yuksekgonul, Bianchi, Boen, Liu, Huang, Guestrin, and Zou (2024) proposed TextGrad, which performs automatic \u201Cdifferentiation\u201D via text by backpropagating LLM-generated textual feedback through computation graphs to optimize compound AI system components, improving GPT-4o zero-shot accuracy on GPQA and achieving substantial gains on LeetCode-Hard. Yang, Wang, Lu, Liu, Le, Zhou, and Chen (2023) developed OPRO, which uses LLMs as black-box optimizers by describing optimization tasks in natural language, with the LLM iteratively generating new prompt candidates from a meta-prompt containing previous solutions with scores, outperforming human-designed prompts by up to 8% on GSM8K and 50% on Big-Bench Hard.")
]));

children.push(p([
  t("Evolutionary approaches have done well here. Guo et al. (2023) combined LLMs with evolutionary algorithms in EvoPrompt, outperforming human-engineered prompts across 31 datasets in language understanding, generation, and reasoning. Fernando, Banarse, Michalewski, Osindero, and Rockt\u00E4schel (2023) introduced PromptBreeder, which evolves both task-prompts and the mutation-prompts that generate them in a self-referential loop. Pryzant, Iter, Li, Lee, Zhu, and Zeng (2023) proposed ProTeGi, which uses LLM-generated natural language \"gradients\" (criticisms of current prompt performance) to iteratively edit prompts, reaching up to 31% improvement on classification tasks.")
]));

children.push(p([
  t("More recent work targets agentic systems directly. Shinn, Cassano, Gopinath, Narasimhan, and Yao (2023) introduced Reflexion, where agents verbally reflect on task feedback and store reflections in episodic memory, producing gains on AlfWorld, HotPotQA, and HumanEval. Hu, Lu, and Clune (2024) proposed ADAS (Automated Design of Agentic Systems), defining agents in code and using a meta-agent to iteratively program new designs from an ever-growing archive, outperforming hand-designed agents on several benchmarks. Cheng, Nie, and Swaminathan (2024) developed Trace and OptoPrime, framing workflow optimization over execution traces with rich feedback and beating DSPy's COPRO by roughly 10% on Big-Bench Hard. Zhang et al. (2024) introduced AgentOptimizer, treating an agent's tools as learnable parameters that an LLM-based optimizer can add, revise, or remove. Wu et al. (2024) proposed AvaTaR, using contrastive reasoning to generate prompts for tool-assisted knowledge retrieval.")
]));

children.push(p([
  t("Across all of this work, evaluations stay within question answering, classification, mathematical reasoning, coding, and simplified interactive environments. DSPy's optimizers are validated on GSM8K and HotPotQA; TextGrad on GPQA and LeetCode; OPRO on GSM8K and Big-Bench Hard; Reflexion on AlfWorld and HumanEval; ADAS on ARC and DROP; AvaTaR on STaRK. None of these are structured multi-turn tool-calling benchmarks with realistic user simulation, domain-specific policies, and enterprise-grade success criteria. The \u03C4-bench family, which tests exactly these conditions, has not been used as an optimization target for any automated prompt evolution method. The optimization tools exist. The benchmarks exist. But nobody has connected them.")
]));

// ============================================================
// 2.5 TEACHER-STUDENT DISTILLATION
// ============================================================

children.push(h2("2.5 From Weight-Level Distillation to Prompt-Level Knowledge Transfer"));

children.push(p([
  t("Knowledge distillation, where a strong model transfers knowledge to a weaker one, has a long history in machine learning. Hinton, Vinyals, and Dean (2015) trained a smaller \"student\" to replicate the soft probability distributions of a larger \"teacher\" via temperature-scaled softmax, showing that knowledge can be compressed into smaller, deployable models with most performance retained. In NLP, Sanh, Debut, Chaumond, and Wolf (2019) applied distillation during pre-training to produce DistilBERT, 40% smaller than BERT while retaining 97% of its language understanding. Jiao, Yin, Shang, Jiang, Chen, Li, Wang, and Liu (2020) pushed further with TinyBERT, distilling at multiple Transformer layers to produce a model 7.5x smaller and 9.4x faster than BERT-Base at 96.8% of its performance.")
]));

children.push(p([
  t("Large language models shifted distillation from soft probability matching to output-level transfer. Taori et al. (2023) fine-tuned LLaMA-7B on 52,000 instruction-following examples generated by text-davinci-003 to create Stanford Alpaca, which behaves similarly to GPT-3.5 for under 600 US dollars. Chiang et al. (2023) fine-tuned LLaMA-13B on roughly 70,000 user-shared ChatGPT conversations to create Vicuna, reaching about 90% of ChatGPT quality. Wang, Kordi, Mishra, Liu, Smith, Khashabi, and Hajishirzi (2023) formalized this with Self-Instruct, where a model generates its own instruction-following training data through a bootstrapping pipeline starting from 175 seed tasks. The teacher's knowledge here is no longer transferred as probability distributions but as behavioral outputs used to train the student's weights.")
]));

children.push(p([
  t("More recent work adds iterative, failure-driven knowledge transfer that resembles the approach taken here. Jiang, Chan, Chen, and Wang (2023) proposed Lion, an adversarial distillation loop where the teacher finds instructions the student fails on and generates harder examples, transferring knowledge from ChatGPT to a smaller model that beats Vicuna on Big-Bench Hard. Xu et al. (2023) introduced Evol-Instruct through WizardLM, where a strong LLM progressively rewrites simple instructions into more complex ones through in-depth and in-breadth evolution. Of existing methods, this comes closest to prompt-level distillation, though the final step still involves fine-tuning weights. Zheng et al. (2023) studied the LLM-as-judge paradigm systematically and showed that GPT-4 agrees with human preferences over 80% of the time, validating the idea that a strong model can serve as a diagnostic supervisor.")
]));

children.push(p([
  t("An important precedent for prompt-level transfer is SPoT (Vu, Lester, Constant, Al-Rfou, & Cer, 2022), which showed that soft prompts learned for one task can initialize prompts for new tasks, improving performance across 26 NLP tasks. This establishes that knowledge encoded in prompts, not just in weights, can be reused across contexts. Constitutional AI (Bai et al., 2022) is another form of model-to-model transfer at the principle level, where a model's critiques encoded as natural language rules shape another model's behavior. The trajectory is clear: from weight-level distillation (Hinton et al.) through output-level distillation (Alpaca, Vicuna) to instruction-level transfer (WizardLM, CAI) to prompt-level transfer (SPoT), knowledge transfer has gotten progressively lighter, cheaper, and more reversible. This thesis takes the next step: using a strong teacher model to iteratively optimize the prompts and tool descriptions of a weaker student, transferring knowledge without modifying any weights.")
]));

// ============================================================
// 2.6 THE RESEARCH GAP
// ============================================================

children.push(h2("2.6 Identifying the Research Gap"));

children.push(p([
  t("The previous sections cover three research areas that have developed mostly in parallel: agentic benchmarking, automated prompt optimization, and teacher\u2013student knowledge transfer. No existing work combines automated prompt optimization driven by a frontier teacher model with validation on structured tool-agent-user benchmarks. Several recent papers approach this intersection from different directions but leave the gap open.")
]));

children.push(p([
  t("The closest existing work is GEPA (Agrawal, Tan, Soylu, Ziems, Khare, Opsahl-Ong, Singhvi, Shandilya, Ryan, Jiang, Potts, Sen, Dimakis, Stoica, Klein, Zaharia, & Khattab, 2025), a Genetic-Pareto prompt optimizer integrated into DSPy that uses natural language reflection from a stronger model to diagnose failures from execution traces and propose targeted mutations for a weaker task model, outperforming reinforcement learning baselines by up to 20%. GEPA has automated prompt optimization and implicitly employs a teacher\u2013student paradigm, but its evaluations are on reasoning benchmarks (HotPotQA, AIME) and instruction-following (IFBench)\u2014not on multi-turn customer service benchmarks with tool calls and domain policies.")
]));

children.push(p([
  t("Pei, Zhen, Kai, Pan, Wang, Yuan, and Yu (2025) proposed SCOPE, which frames agent prompt management as an online optimization problem, synthesizing guidelines from execution traces via a dual-stream mechanism. SCOPE provides automated prompt evolution for agents and tests on agentic benchmarks (GAIA, HLE), but it does not employ a teacher\u2013student paradigm where a stronger model explicitly diagnoses and patches the behavior of a weaker one. Choudhury and Sodhi (2024) introduced LEAP, an iterative framework where an AI expert teacher with privileged state information provides corrective feedback to a weaker student agent. LEAP has a clear teacher\u2013student architecture and evaluates on interactive agent benchmarks (ALFWorld, WebShop), but it improves the student via fine-tuning\u2014weight updates rather than prompt optimization\u2014and does not target tool-calling customer service benchmarks.")
]));

children.push(p([
  t("Reflexion (Shinn et al., 2023) improves agent performance through verbal self-reflection without weight updates, but reflections are ephemeral per-episode memory rather than permanent prompt patches, and there is no separate teacher model. ADAS (Hu et al., 2024) automates agent design including prompt discovery but operates at the level of entire agent architectures rather than iterative prompt patching and lacks an explicit teacher\u2013student mechanism.")
]));

children.push(p([
  t("The pieces are all there but have not been assembled. Agentic benchmarks like \u03C4\u00B2-bench show precisely where tool-using agents fail and provide reproducible, domain-specific success criteria. Automated prompt optimization (DSPy, TextGrad, GEPA) shows that prompts and tool descriptions can be improved algorithmically at costs far below fine-tuning. Teacher\u2013student distillation, from Hinton's original work through Alpaca and Lion to LLM-as-judge, shows that a strong model can reliably supervise a weaker one. What this thesis contributes is the empirical demonstration that a frontier reasoning model can iteratively evolve the prompts and tool descriptions of a smaller, cheaper model on a structured tool-agent-user benchmark, producing measurable reliability improvements without modifying any model weights. The approach operates at the prompt level (no retraining), is validated on \u03C4\u00B2-bench with standardized metrics, and mirrors the operational reality where a capable but expensive system improves the behavior of a cheaper execution-tier agent.")
]));


module.exports = children;
