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
  t("This chapter reviews the literature that motivates and positions the present work. The review is organized around six interconnected propositions that, taken together, identify a research gap at the intersection of agentic benchmarking, automated prompt optimization, and teacher\u2013student knowledge transfer. Each subsection advances a distinct claim supported by existing scholarship: that tool-using language model agents remain unreliable at enterprise scale; that static prompting and scaffolding techniques, while valuable, reach a performance ceiling; that reinforcement learning from human feedback and fine-tuning, though effective, are impractical for rapid domain-specific adaptation; that automated prompt optimization methods are powerful yet untested on structured tool-agent-user benchmarks; that teacher\u2013student knowledge distillation is well-established at the weight level and increasingly explored at the output level; and that the specific combination of teacher-model-driven prompt evolution validated on agentic tool-use benchmarks remains an open problem. The chapter concludes by synthesizing these strands into the research gap that this thesis addresses.")
]));

// ============================================================
// 2.1 THE ENTERPRISE RELIABILITY GAP
// ============================================================

children.push(h2("2.1 The Enterprise Reliability Gap in Tool-Using Agents"));

children.push(p([
  t("The past two years have seen a proliferation of benchmarks designed to evaluate large language models not merely as text generators but as autonomous agents capable of multi-turn interaction, tool invocation, and policy adherence. The \u03C4-bench family is central to this thesis. Yao, Shinn, Razavi, and Narasimhan (2024) introduced \u03C4-bench as a benchmark that operationalizes tool\u2013agent\u2013user interaction into measurable success criteria across retail and airline customer-service domains. Their results revealed that even GPT-4o succeeded on fewer than half of all tasks, and the pass"),
  t("k", { superScript: true }),
  t(" reliability metric\u2014which measures the probability of solving the same task "),
  ti("k"),
  t(" consecutive times\u2014showed that pass"),
  t("8", { superScript: true }),
  t(" dropped below 25% in the retail domain. Barres, Dong, Ray, Si, and Narasimhan (2025) extended this work with \u03C4\u00B2-bench, introducing a dual-control environment where both the agent and a simulated user have access to tools and databases, and adding a telecom domain. The expanded setup exposed further failure modes, particularly in scenarios requiring the user to perform physical actions such as troubleshooting network equipment, and confirmed that frontier models remain far from reliable even in the enriched evaluation setting.")
]));

children.push(p([
  t("These findings are not isolated to the \u03C4-bench family. Liu et al. (2023) presented AgentBench, the first systematic multi-dimensional benchmark evaluating LLMs as agents across eight interactive environments including operating system interaction, database operations, and web browsing. Testing twenty-nine models, they found a significant performance gap between top commercial systems and open-source alternatives, identifying poor long-term reasoning, decision-making, and instruction following as the primary obstacles. In a complementary line of work, Jimenez, Yang, Wettig, Yao, Pei, Press, and Narasimhan (2024) introduced SWE-bench, a collection of 2,294 real-world software engineering tasks drawn from GitHub issues. At publication, the best-performing model solved only 1.96% of issues, establishing that autonomous multi-step tool use remains fundamentally unreliable even in code-centric domains where LLMs are considered strongest.")
]));

children.push(p([
  t("Benchmarks targeting specific tool-use capabilities reinforce this picture. Qin et al. (2023) introduced ToolBench with over 16,000 real-world RESTful APIs, finding that open-source instruction-tuned models achieved a zero percent pass rate on tool-use tasks and that even ChatGPT required a novel depth-first search decision tree to achieve reasonable performance. Li et al. (2023) proposed API-Bank with 73 API tools across 314 dialogues, identifying persistent failure modes in parameter extraction, API selection, and sequential planning even for GPT-4. Mialon et al. (2023) presented GAIA, 466 real-world questions requiring reasoning, browsing, and tool-use proficiency, where human respondents scored 92% versus only 15% for GPT-4 with plugins\u2014a 77-point gap that inverts the typical narrative of LLMs outperforming humans on standard benchmarks.")
]));

children.push(p([
  t("Two recent meta-analyses provide the conceptual framing for interpreting these results. Kapoor, Stroebl, Siegel, Nadgir, and Narayanan (2024) conducted a critical analysis of agent benchmarking practices, showing that state-of-the-art agents exhibit fifty-fold cost variation for similar accuracy levels and that complex agent architectures achieve marginal accuracy gains at exponential cost\u2014directly relevant to the thesis\u2019s argument that prompt-level optimization offers a more efficient path to improvement than architectural scaling. Most consequentially, Rabanser, Kapoor, Kirgis, Liu, Utpala, and Narayanan (2025) proposed twelve metrics decomposing agent reliability across consistency, robustness, predictability, and safety. Testing fourteen models across eighteen months on GAIA and \u03C4-bench, they identified a persistent "),
  ti("capability\u2013reliability gap"),
  t(": accuracy improves faster than reliability. Their work explicitly argues that enterprise autonomous operation requires three to five nines of performance (99.9%\u201399.999%) and that current LLM agents are not on track to reach this threshold through scaling alone.")
]));

// ============================================================
// 2.2 STATIC PROMPTING CEILING
// ============================================================

children.push(h2("2.2 The Ceiling of Static Prompting and Scaffolding"));

children.push(p([
  t("A substantial body of work has sought to improve agent performance through better prompt design and execution scaffolding. Chain-of-thought prompting, introduced by Wei et al. (2022), demonstrated that a small number of hand-crafted reasoning exemplars can dramatically improve performance on arithmetic, commonsense, and symbolic reasoning tasks, with PaLM-540B achieving state-of-the-art results on GSM8K. The ReAct framework (Yao, Zhao, Yu, Du, Shafran, Narasimhan, & Cao, 2023) extended this by interleaving reasoning traces with task-specific actions, enabling models to interface with external tools while maintaining reasoning chains. ReAct improved over both pure chain-of-thought and pure action-generation baselines on question answering, fact verification, and interactive decision-making. Yao, Yu, Zhao, Shafran, Griffiths, Cao, and Narasimhan (2023) further generalized the approach with Tree of Thoughts, enabling LMs to explore multiple reasoning paths via tree search with self-evaluation, achieving 74% success on Game of 24 versus chain-of-thought\u2019s 4%.")
]));

children.push(p([
  t("On the tool-use side, the introduction of function calling by OpenAI (2023) shifted interaction from free-form text generation to schema-driven structured output, acknowledging that pure natural-language prompting is insufficient for reliable tool invocation. Schick et al. (2023) proposed Toolformer, training language models in a self-supervised manner to autonomously invoke external tools, achieving zero-shot performance competitive with much larger models. Patil, Zhang, Wang, and Gonzalez (2023) fine-tuned LLaMA to surpass GPT-4 on API call generation through Gorilla, while simultaneously showing that GPT-4 frequently hallucinates incorrect API usage when relying on prompting alone. Willard and Louf (2023) approached the format reliability problem through constrained decoding with finite-state machines, guaranteeing valid structured output but addressing only output format rather than reasoning or planning.")
]));

children.push(p([
  t("Despite these genuine advances, the literature reveals fundamental limitations of static approaches. The core problem is that all of these techniques fix the agent\u2019s behavioral repertoire at design time. ReAct exemplars are hand-crafted and task-specific; function schemas consume tokens and require careful engineering; chain-of-thought reasoning is strongly model-size-dependent, emerging only at approximately 100 billion parameters (Wei et al., 2022). Brown et al. (2020) established that in-context few-shot learning has task-dependent ceilings, with GPT-3 failing on tasks like ANLI and QuAC. Zhou, Muresanu, Han, Paster, Pitis, Chan, and Ba (2022) found through their Automatic Prompt Engineer (APE) work that optimal prompts are fragile\u2014small wording changes alter effectiveness\u2014supporting the characterization of prompt engineering as program synthesis over a brittle search space.")
]));

children.push(p([
  t("The most direct empirical evidence for this ceiling comes from Sclar, Choi, Tsvetkov, and Suhr (2023), who demonstrated extreme sensitivity of LLMs to meaning-preserving formatting changes in few-shot prompts, with up to 76 accuracy points of variation on LLaMA-2-13B from changes as trivial as spacing and delimiter choice. This sensitivity persisted even with increased model size, more examples, or instruction tuning. The implication for agent deployment is clear: static prompt scaffolds, however sophisticated, cannot guarantee the consistent behavior that enterprise applications demand. The agent\u2019s performance is contingent on design-time decisions that may be suboptimal or brittle under distribution shift, and there is no mechanism for the agent to adapt when it encounters novel failure modes in production.")
]));

// ============================================================
// 2.3 RLHF IMPRACTICALITY
// ============================================================

children.push(h2("2.3 The Impracticality of Fine-Tuning for Rapid Enterprise Adaptation"));

children.push(p([
  t("Reinforcement learning from human feedback (RLHF) has been the dominant paradigm for aligning language models with human intent. Ouyang et al. (2022) demonstrated with InstructGPT that a 1.3-billion-parameter model trained with human feedback is preferred over 175-billion-parameter GPT-3, establishing the effectiveness of the approach. However, their work also revealed the substantial infrastructure required: labeler-written demonstrations, multi-stage reward modeling, and iterative RL optimization, all demanding extensive human annotation pipelines. The authors noted an \u201Calignment tax\u201D where alignment comes at the cost of performance regressions on public NLP benchmarks. Bai et al. (2022) proposed Constitutional AI (CAI) to reduce the human feedback burden by replacing human harmlessness labels with model-generated critiques guided by constitutional principles, but CAI still requires a complex multi-phase pipeline of supervised self-critique followed by reinforcement learning.")
]));

children.push(p([
  t("Subsequent work has simplified the pipeline but not eliminated its fundamental constraints. Rafailov, Sharma, Mitchell, Manning, Ermon, and Finn (2023) introduced Direct Preference Optimization (DPO), eliminating the separate reward model and RL optimization by directly optimizing the language model on preference data using a classification loss. DPO matches or exceeds PPO-based RLHF with substantially less complexity. However, the core bottleneck\u2014collecting or generating domain-specific preference datasets\u2014remains. Every new company policy or workflow change would require new preference data, making DPO equally impractical for rapid enterprise adaptation. Hu, Shen, Wallis, Allen-Zhu, Li, Wang, Wang, and Chen (2022) reduced fine-tuning costs through LoRA, which injects trainable low-rank matrices while freezing pretrained weights, cutting trainable parameters by up to 10,000\u00D7. While making fine-tuning more accessible, LoRA does not eliminate the need for task-specific training data or the risk of catastrophic forgetting.")
]));

children.push(p([
  t("The limitations of the RLHF paradigm are well-documented. Casper et al. (2023) produced a comprehensive survey taxonomizing RLHF challenges including noisy and biased human feedback, reward hacking, distributional shift, instability, and sycophancy, arguing that RLHF is not a complete alignment framework and that human evaluators miss over half of critical errors. Lin et al. (2024) directly quantified the alignment tax, showing that RLHF alignment degrades pretrained LLM abilities in translation, reading comprehension, and common-sense reasoning, with existing mitigation techniques such as LoRA and regularization proving insufficient. Luo, Yang, Meng, Li, and Zhou (2023) confirmed that catastrophic forgetting during continual fine-tuning affects all model sizes and, counterintuitively, that larger models suffer stronger forgetting\u2014meaning that fine-tuning for one enterprise task (such as compliance checking) risks degrading performance on others (such as customer support).")
]));

children.push(p([
  t("Zhou, Liu, Xu, Iyer, Sun, Mao, Ma, Efrat, Yu, Yu, Zhang, Ghosh, Lewis, Zettlemoyer, and Levy (2023) offered an alternative perspective through LIMA, demonstrating that fine-tuning on just 1,000 carefully curated examples can achieve strong alignment. Their \u201CSuperficial Alignment Hypothesis\u201D\u2014that alignment primarily teaches style and format rather than injecting knowledge\u2014is conceptually aligned with the thesis\u2019s premise that prompt-level interventions can achieve substantial behavioral changes. However, LIMA\u2019s effectiveness depends on extremely careful manual curation, and each new enterprise domain would require expert-curated datasets, making it no more practical for rapid adaptation than RLHF. The collective evidence suggests that while fine-tuning approaches are powerful in principle, they impose costs in data collection, compute, and maintenance that make them unsuitable as a mechanism for the rapid, reversible, domain-specific agent improvement that enterprises require.")
]));

// ============================================================
// 2.4 AUTOMATED PROMPT OPTIMIZATION
// ============================================================

children.push(h2("2.4 Automated Prompt Optimization: Power Without Agentic Validation"));

children.push(p([
  t("A rapidly growing body of work demonstrates that prompts can be optimized automatically, without updating model weights. This section reviews the major approaches and identifies a consistent blind spot: none have been validated on structured tool-agent-user benchmarks.")
]));

children.push(p([
  t("Khattab et al. (2023) introduced DSPy, a framework that abstracts language model pipelines as declarative modules with learnable parameters\u2014prompts and demonstrations\u2014and provides a compiler that automatically optimizes pipelines against a target metric. GPT-3.5 and Llama2-13b self-bootstrap pipelines that outperform expert-created demonstrations by 5\u201346% on multi-hop QA and math reasoning. Yuksekgonul, Bianchi, Boen, Liu, Huang, Guestrin, and Zou (2024) proposed TextGrad, which performs automatic \u201Cdifferentiation\u201D via text by backpropagating LLM-generated textual feedback through computation graphs to optimize compound AI system components, improving GPT-4o zero-shot accuracy on GPQA and achieving substantial gains on LeetCode-Hard. Yang, Wang, Lu, Liu, Le, Zhou, and Chen (2023) developed OPRO, which uses LLMs as black-box optimizers by describing optimization tasks in natural language, with the LLM iteratively generating new prompt candidates from a meta-prompt containing previous solutions with scores, outperforming human-designed prompts by up to 8% on GSM8K and 50% on Big-Bench Hard.")
]));

children.push(p([
  t("Evolutionary approaches have proven particularly effective. Guo et al. (2023) combined LLMs with evolutionary algorithms for discrete prompt optimization through EvoPrompt, significantly outperforming human-engineered prompts across 31 datasets covering language understanding, generation, and reasoning. Fernando, Banarse, Michalewski, Osindero, and Rockt\u00E4schel (2023) introduced PromptBreeder, which evolves both task-prompts and the mutation-prompts that generate them in a self-referential loop. Pryzant, Iter, Li, Lee, Zhu, and Zeng (2023) proposed ProTeGi, using LLM-generated natural language \u201Cgradients\u201D\u2014criticisms of current prompt performance\u2014to iteratively edit prompts, achieving up to 31% improvement on classification tasks.")
]));

children.push(p([
  t("More recent work has begun to target agentic systems specifically. Shinn, Cassano, Gopinath, Narasimhan, and Yao (2023) introduced Reflexion, where language agents verbally reflect on task feedback and maintain reflective text in episodic memory, achieving significant gains on AlfWorld, HotPotQA, and HumanEval. Hu, Lu, and Clune (2024) proposed Automated Design of Agentic Systems (ADAS), which defines agents in code and uses a meta-agent to iteratively program new agent designs based on an ever-growing archive of discoveries, outperforming hand-designed agents on multiple benchmarks. Cheng, Nie, and Swaminathan (2024) developed Trace and OptoPrime, framing workflow optimization as an optimization problem with execution traces and rich feedback, achieving approximately 10% higher accuracy than DSPy\u2019s COPRO on Big-Bench Hard. Zhang et al. (2024) introduced AgentOptimizer, treating an LLM agent\u2019s function and tool set as learnable parameters and using an LLM-based optimizer to iteratively add, revise, or remove tools. Wu et al. (2024) proposed AvaTaR, which uses contrastive reasoning to provide holistic prompts for tool-assisted knowledge retrieval tasks.")
]));

children.push(p([
  t("Despite the breadth and sophistication of this literature, a consistent pattern emerges: evaluations are confined to question answering, classification, mathematical reasoning, coding, and simplified interactive environments. DSPy\u2019s optimizers are validated on GSM8K and HotPotQA; TextGrad on GPQA and LeetCode; OPRO on GSM8K and Big-Bench Hard; Reflexion on AlfWorld and HumanEval; ADAS on ARC and DROP; AvaTaR on STaRK. None of these are structured multi-turn tool-calling benchmarks with realistic user simulation, domain-specific policies, and enterprise-grade success criteria. The \u03C4-bench family\u2014which operationalizes exactly these conditions\u2014has not been used as an optimization target for any automated prompt evolution method. This is the critical gap for the present work: the tools exist, the benchmarks exist, but the connection between them has not been made.")
]));

// ============================================================
// 2.5 TEACHER-STUDENT DISTILLATION
// ============================================================

children.push(h2("2.5 From Weight-Level Distillation to Prompt-Level Knowledge Transfer"));

children.push(p([
  t("The idea that a strong model can transfer knowledge to a weaker one is well-established in machine learning. Hinton, Vinyals, and Dean (2015) introduced knowledge distillation, training a smaller \u201Cstudent\u201D model to replicate the soft probability distributions of a larger \u201Cteacher\u201D model via temperature-scaled softmax. This foundational work demonstrated that knowledge can be compressed from cumbersome models into smaller, deployable ones while retaining most performance. In NLP, Sanh, Debut, Chaumond, and Wolf (2019) applied distillation during pre-training to produce DistilBERT, reducing BERT\u2019s size by 40% while retaining 97% of its language understanding capabilities. Jiao, Yin, Shang, Jiang, Chen, Li, Wang, and Liu (2020) achieved further compression with TinyBERT through Transformer distillation at multiple layers, producing a model 7.5\u00D7 smaller and 9.4\u00D7 faster than BERT-Base at 96.8% of its performance.")
]));

children.push(p([
  t("The emergence of large language models shifted the distillation paradigm from soft probability matching to output-level transfer. Taori et al. (2023) demonstrated with Stanford Alpaca that LLaMA-7B fine-tuned on 52,000 instruction-following examples generated by text-davinci-003 achieves behavior qualitatively similar to GPT-3.5 for under 600 US dollars. Chiang et al. (2023) fine-tuned LLaMA-13B on approximately 70,000 user-shared ChatGPT conversations to create Vicuna, achieving roughly 90% of ChatGPT quality. Wang, Kordi, Mishra, Liu, Smith, Khashabi, and Hajishirzi (2023) formalized this pattern through Self-Instruct, where a language model generates its own instruction-following training data via a bootstrapping pipeline starting from 175 seed tasks. These works represent a paradigm shift: the teacher\u2019s knowledge is transferred not through soft probability distributions but through behavioral outputs that train the student\u2019s weights.")
]));

children.push(p([
  t("More recent work has introduced iterative, failure-driven knowledge transfer that more closely resembles the present thesis\u2019s approach. Jiang, Chan, Chen, and Wang (2023) proposed Lion, an adversarial distillation loop where the teacher identifies hard instructions where the student fails and generates new challenging examples, transferring knowledge from ChatGPT to a smaller model that surpasses Vicuna on Big-Bench Hard. Xu et al. (2023) introduced Evol-Instruct through WizardLM, where a strong LLM progressively rewrites simple instructions into more complex ones through in-depth and in-breadth evolution\u2014the closest existing analog to prompt-level distillation, though the final step still involves fine-tuning weights. Zheng et al. (2023) systematically studied the LLM-as-judge paradigm, establishing that a strong model (GPT-4) can provide reliable supervisory signals with over 80% agreement with human preferences, validating the teacher-model diagnostic mechanism that the thesis employs.")
]));

children.push(p([
  t("A crucial precedent for prompt-level transfer is the work of Vu, Lester, Constant, Al-Rfou, and Cer (2022) on SPoT, which demonstrated that soft prompts learned for one task can be transferred to initialize prompts for new tasks, improving performance across 26 NLP tasks. This establishes the theoretical basis for prompt-level knowledge transfer\u2014that knowledge encoded in prompts (rather than model weights) can be reused across contexts. Constitutional AI (Bai et al., 2022) represents another form of model-to-model knowledge transfer at the principle level, where a model\u2019s critiques encoded as natural language rules shape another model\u2019s behavior. The trajectory from weight-level distillation (Hinton et al.) through output-level distillation (Alpaca, Vicuna) to instruction-level transfer (WizardLM, CAI) to prompt-level transfer (SPoT) reveals a clear evolutionary direction: knowledge transfer mechanisms are becoming progressively lighter, cheaper, and more reversible. The present thesis extends this trajectory to its logical next step: using a strong teacher model to iteratively optimize the prompts and tool descriptions of a weaker student model, achieving knowledge transfer without modifying any weights.")
]));

// ============================================================
// 2.6 THE RESEARCH GAP
// ============================================================

children.push(h2("2.6 Identifying the Research Gap"));

children.push(p([
  t("The preceding sections establish three mature research streams\u2014agentic benchmarking, automated prompt optimization, and teacher\u2013student knowledge transfer\u2014that have developed largely in parallel. The research gap this thesis addresses lies at their intersection: no existing work combines automated prompt optimization driven by a frontier teacher model with validation on structured tool-agent-user benchmarks. Several recent papers approach this intersection from different directions but leave the gap open.")
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
  t("In summary, the literature offers three well-developed components that have not been assembled into a single framework. Agentic benchmarks such as \u03C4\u00B2-bench tell us precisely where tool-using agents fail and provide reproducible, domain-specific success criteria. Automated prompt optimization methods such as DSPy, TextGrad, and GEPA demonstrate that prompts and tool descriptions can be improved algorithmically at costs far below fine-tuning. Teacher\u2013student distillation, from Hinton\u2019s foundational work through Alpaca and Lion to LLM-as-judge, establishes that a strong model can reliably supervise a weaker one. What is missing\u2014and what this thesis contributes\u2014is the empirical demonstration that a frontier reasoning model can iteratively evolve the prompts and tool descriptions of a smaller, cheaper model on a structured tool-agent-user benchmark, achieving measurable reliability improvements without modifying any model weights. This approach is practical because it operates at the prompt level rather than requiring retraining; it is measurable because it is validated on \u03C4\u00B2-bench with standardized metrics; and it is enterprise-aligned because it mirrors the operational reality where a more capable (and expensive) system improves the behavior of a cheaper execution-tier agent.")
]));

// ============================================================
// REFERENCES
// ============================================================

children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("References"));

const refs = [
  `Agrawal, L. A., Tan, S., Soylu, D., Ziems, N., Khare, R., Opsahl-Ong, K., Singhvi, A., Shandilya, H., Ryan, M. J., Jiang, M., Potts, C., Sen, K., Dimakis, A. G., Stoica, I., Klein, D., Zaharia, M., & Khattab, O. (2025). GEPA: Reflective prompt evolution can outperform reinforcement learning. arXiv preprint arXiv:2507.19457.`,
  `Bai, Y., Kadavath, S., Kundu, S., Askell, A., Kernion, J., Jones, A., Chen, A., Goldie, A., Mirhoseini, A., McKinnon, C., Chen, C., Olsson, C., Olah, C., Hernandez, D., Drain, D., Ganguli, D., Li, D., Tran-Johnson, E., Perez, E., \u2026 Kaplan, J. (2022). Constitutional AI: Harmlessness from AI feedback. arXiv preprint arXiv:2212.08073.`,
  `Barres, V., Dong, H., Ray, S., Si, X., & Narasimhan, K. (2025). \u03C4\u00B2-bench: Evaluating conversational agents in a dual-control environment. arXiv preprint arXiv:2506.07982.`,
  `Brown, T. B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., Neelakantan, A., Shyam, P., Sastry, G., Askell, A., Agarwal, S., Herbert-Voss, A., Krueger, G., Henighan, T., Child, R., Ramesh, A., Ziegler, D. M., Wu, J., Winter, C., \u2026 Amodei, D. (2020). Language models are few-shot learners. Advances in Neural Information Processing Systems, 33, 1877\u20131901.`,
  `Casper, S., Davies, X., Shi, C., Gilbert, T. K., Scheurer, J., Rando, J., Freedman, R., Korbak, T., Lindner, D., Freire, P., Wang, T., Marks, S., Segerie, C.-R., Carroll, M., Peng, A., Christoffersen, P., Damani, M., Slocum, S., Anwar, U., \u2026 Hadfield-Menell, D. (2023). Open problems and fundamental limitations of reinforcement learning from human feedback. Transactions on Machine Learning Research.`,
  `Cheng, C.-A., Nie, A., & Swaminathan, A. (2024). Trace is the next AutoDiff: Generative optimization with rich feedback, execution traces, and LLMs. Advances in Neural Information Processing Systems, 37. arXiv preprint arXiv:2406.16218.`,
  `Chiang, W.-L., Li, Z., Lin, Z., Sheng, Y., Wu, Z., Zhang, H., Zheng, L., Zhuang, S., Zhuang, Y., Gonzalez, J. E., Stoica, I., & Xing, E. P. (2023). Vicuna: An open-source chatbot impressing GPT-4 with 90%* ChatGPT quality. LMSYS Blog.`,
  `Choudhury, S., & Sodhi, P. (2024). Better than your teacher: LLM agents that learn from privileged AI feedback. arXiv preprint arXiv:2410.05434.`,
  `Fernando, C., Banarse, D., Michalewski, H., Osindero, S., & Rockt\u00E4schel, T. (2023). PromptBreeder: Self-referential self-improvement via prompt evolution. arXiv preprint arXiv:2309.16797.`,
  `Guo, Q., Wang, R., Guo, J., Li, B., Song, K., Tan, X., Liu, G., Bian, J., & Yang, Y. (2023). Connecting LLMs with evolutionary algorithms yields powerful prompt optimizers. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Hinton, G., Vinyals, O., & Dean, J. (2015). Distilling the knowledge in a neural network. arXiv preprint arXiv:1503.02531.`,
  `Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large language models. Proceedings of the Tenth International Conference on Learning Representations.`,
  `Hu, S., Lu, C., & Clune, J. (2024). Automated design of agentic systems. Proceedings of the Thirteenth International Conference on Learning Representations. arXiv preprint arXiv:2408.08435.`,
  `Jiang, Y., Chan, C., Chen, M., & Wang, W. (2023). Lion: Adversarial distillation of proprietary large language models. Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing, 3134\u20133154.`,
  `Jiao, X., Yin, Y., Shang, L., Jiang, X., Chen, X., Li, L., Wang, F., & Liu, Q. (2020). TinyBERT: Distilling BERT for natural language understanding. Findings of the Association for Computational Linguistics: EMNLP 2020, 4163\u20134174.`,
  `Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., & Narasimhan, K. (2024). SWE-bench: Can language models resolve real-world GitHub issues? Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Kapoor, S., Stroebl, B., Siegel, Z. S., Nadgir, N., & Narayanan, A. (2024). AI agents that matter. Transactions on Machine Learning Research.`,
  `Khattab, O., Singhvi, A., Maheshwari, P., Zhang, Z., Santhanam, K., Vardhamanan, S., Haq, S., Sharma, A., Joshi, T. T., Moazam, H., Miller, H., Zaharia, M., & Potts, C. (2023). DSPy: Compiling declarative language model calls into self-improving pipelines. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Li, M., Zhao, Y., Yu, B., Song, F., Li, H., Yu, H., Li, Z., Huang, F., & Li, Y. (2023). API-Bank: A comprehensive benchmark for tool-augmented LLMs. Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing, 3102\u20133116.`,
  `Lin, Y., Lin, H., Xiong, W., Diao, S., Liu, J., Zhang, J., Pan, R., Wang, H., Hu, W., Zhang, H., Dong, H., Pi, R., Zhao, H., Jiang, N., Ji, H., Yao, Y., & Zhang, T. (2024). Mitigating the alignment tax of RLHF. Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing.`,
  `Liu, X., Yu, H., Zhang, H., Xu, Y., Lei, X., Lai, H., Gu, Y., Ding, H., Men, K., Yang, K., Zhang, S., Deng, X., Zeng, A., Du, Z., Zhang, C., Shen, S., Zhang, T., Su, Y., Sun, H., \u2026 Tang, J. (2023). AgentBench: Evaluating LLMs as agents. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Luo, Y., Yang, Z., Meng, F., Li, Y., & Zhou, J. (2023). An empirical study of catastrophic forgetting in large language models during continual fine-tuning. arXiv preprint arXiv:2308.08747.`,
  `Mialon, G., Fourrier, C., Swift, C., Wolf, T., LeCun, Y., & Scialom, T. (2023). GAIA: A benchmark for general AI assistants. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `OpenAI. (2023, June 13). Function calling and other API updates. https://openai.com/index/function-calling-and-other-api-updates/`,
  `Ouyang, L., Wu, J., Jiang, X., Almeida, D., Wainwright, C. L., Mishkin, P., Zhang, C., Agarwal, S., Slama, K., Ray, A., Schulman, J., Hilton, J., Kelton, F., Miller, L., Simens, M., Askell, A., Welinder, P., Christiano, P., Leike, J., & Lowe, R. (2022). Training language models to follow instructions with human feedback. Advances in Neural Information Processing Systems, 35.`,
  `Patil, S. G., Zhang, T., Wang, X., & Gonzalez, J. E. (2023). Gorilla: Large language model connected with massive APIs. Advances in Neural Information Processing Systems, 37.`,
  `Pei, Z., Zhen, H.-L., Kai, S., Pan, S. J., Wang, Y., Yuan, M., & Yu, B. (2025). SCOPE: Self-evolving context optimization via prompt evolution. arXiv preprint arXiv:2512.15374.`,
  `Pryzant, R., Iter, D., Li, J., Lee, Y. T., Zhu, C., & Zeng, M. (2023). Automatic prompt optimization with \u201Cgradient descent\u201D and beam search. Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing, 7957\u20137968.`,
  `Qin, Y., Liang, S., Ye, Y., Zhu, K., Yan, L., Lu, Y., Lin, Y., Cong, X., Tang, X., Qian, B., Zhao, S., Tian, R., Xie, R., Zhou, J., Gerstein, M., Li, D., Liu, Z., & Sun, M. (2023). ToolLLM: Facilitating large language models to master 16000+ real-world APIs. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Rabanser, S., Kapoor, S., Kirgis, P., Liu, K., Utpala, S., & Narayanan, A. (2025). Towards a science of AI agent reliability. arXiv preprint arXiv:2602.16666.`,
  `Rafailov, R., Sharma, A., Mitchell, E., Manning, C. D., Ermon, S., & Finn, C. (2023). Direct preference optimization: Your language model is secretly a reward model. Advances in Neural Information Processing Systems, 36.`,
  `Sanh, V., Debut, L., Chaumond, J., & Wolf, T. (2019). DistilBERT, a distilled version of BERT: Smaller, faster, cheaper and lighter. arXiv preprint arXiv:1910.01108.`,
  `Schick, T., Dwivedi-Yu, J., Dess\u00EC, R., Raileanu, R., Lomeli, M., Hambro, E., Zettlemoyer, L., Cancedda, N., & Scialom, T. (2023). Toolformer: Language models can teach themselves to use tools. Advances in Neural Information Processing Systems, 36.`,
  `Sclar, M., Choi, Y., Tsvetkov, Y., & Suhr, A. (2023). Quantifying language models\u2019 sensitivity to spurious features in prompt design. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language agents with verbal reinforcement learning. Advances in Neural Information Processing Systems, 36.`,
  `Taori, R., Gulrajani, I., Zhang, T., Dubois, Y., Li, X., Guestrin, C., Liang, P., & Hashimoto, T. B. (2023). Stanford Alpaca: An instruction-following LLaMA model. Stanford CRFM.`,
  `Vu, T., Lester, B., Constant, N., Al-Rfou, R., & Cer, D. (2022). SPoT: Better frozen model adaptation through soft prompt transfer. Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics, 5286\u20135300.`,
  `Wang, Y., Kordi, Y., Mishra, S., Liu, A., Smith, N. A., Khashabi, D., & Hajishirzi, H. (2023). Self-Instruct: Aligning language models with self-generated instructions. Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics, 13484\u201313508.`,
  `Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q. V., & Zhou, D. (2022). Chain-of-thought prompting elicits reasoning in large language models. Advances in Neural Information Processing Systems, 35.`,
  `Willard, B. T., & Louf, R. (2023). Efficient guided generation for large language models. arXiv preprint arXiv:2307.09702.`,
  `Wu, S., Zhao, S., Huang, Q., Huang, K., Yasunaga, M., Cao, K., Ioannidis, V. N., Subbian, K., Leskovec, J., & Zou, J. (2024). AvaTaR: Optimizing LLM agents for tool-assisted knowledge retrieval. Advances in Neural Information Processing Systems, 37.`,
  `Xu, C., Sun, Q., Zheng, K., Geng, X., Zhao, P., Feng, J., Tao, C., & Jiang, D. (2023). WizardLM: Empowering large language models to follow complex instructions. arXiv preprint arXiv:2304.12244.`,
  `Yang, C., Wang, X., Lu, Y., Liu, H., Le, Q. V., Zhou, D., & Chen, X. (2023). Large language models as optimizers. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Yao, S., Shinn, N., Razavi, P., & Narasimhan, K. (2024). \u03C4-bench: A benchmark for tool-agent-user interaction in real-world domains. arXiv preprint arXiv:2406.12045.`,
  `Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., & Narasimhan, K. (2023). Tree of thoughts: Deliberate problem solving with large language models. Advances in Neural Information Processing Systems, 36.`,
  `Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. Proceedings of the Eleventh International Conference on Learning Representations.`,
  `Yuksekgonul, M., Bianchi, F., Boen, J., Liu, S., Huang, Z., Guestrin, C., & Zou, J. (2024). TextGrad: Automatic \u201Cdifferentiation\u201D via text. Advances in Neural Information Processing Systems, 37.`,
  `Zhang, S., Zhang, J., Liu, J., Liu, L., Peng, H., Li, L., Shen, Y., & Wang, C. (2024). AgentOptimizer: Offline training of language model agents with functions as learnable weights. arXiv preprint arXiv:2402.11359.`,
  `Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. Advances in Neural Information Processing Systems, 36.`,
  `Zhou, C., Liu, P., Xu, P., Iyer, S., Sun, J., Mao, Y., Ma, X., Efrat, A., Yu, P., Yu, L., Zhang, S., Ghosh, G., Lewis, M., Zettlemoyer, L., & Levy, O. (2023). LIMA: Less is more for alignment. Advances in Neural Information Processing Systems, 36.`,
  `Zhou, Y., Muresanu, A. I., Han, Z., Paster, K., Pitis, S., Chan, H., & Ba, J. (2022). Large language models are human-level prompt engineers. Proceedings of the Eleventh International Conference on Learning Representations.`,
];

refs.forEach(ref => {
  children.push(p([t(ref)], {
    spacing: { after: 160, line: 360 },
    indent: { left: 720, hanging: 720 },
    alignment: AlignmentType.LEFT
  }));
});

module.exports = children;
