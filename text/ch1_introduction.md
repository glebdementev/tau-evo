# 1. Introduction

Large language models have rapidly moved from research demonstrations to operational infrastructure. Within customer service alone, enterprises are deploying LLM-based agents that hold multi-turn conversations, enforce domain-specific policies, and invoke back-end tools on the customer's behalf [@barres2025; @huang2025crmarena]. The economic incentive is clear: a capable agent can resolve routine tickets at a fraction of the cost and latency of a human operator, and the best frontier models already achieve impressive scores on benchmarks designed to approximate these workflows [@yao2024; @barres2025]. Yet a persistent gap separates benchmark performance from enterprise deployment. Top models reach roughly 98% on the τ²-bench telecom domain [@anthropic2025], while production customer-service systems typically require four-nines reliability—99.99% task success—before organizations are willing to remove the human safety net [@rabanser2025]. Bridging this gap is the central concern of this thesis.

The difficulty is not that language models lack raw capability. The GPT-4 family [@openai2024], Claude [@anthropic2025], and open alternatives such as Qwen3 [@qwen2025] can reason over multi-step plans, generate syntactically valid tool calls, and recover from intermediate errors when prompted carefully. What they cannot do, once deployed, is *learn*. A static agent that fails on a policy edge case on Monday will fail on the same edge case on Tuesday—and on every subsequent encounter—unless a human engineer manually diagnoses the failure, rewrites the prompt or tool schema, and re-deploys the agent. At enterprise scale, where thousands of edge cases accumulate across dozens of policy domains, this manual remediation loop becomes the primary bottleneck to adoption [@kapoor2024; @rabanser2025].

Three bodies of literature converge on this problem without fully solving it: agentic benchmarking, prompt and tool engineering, and model alignment. The following sections review each in turn, identify the gap that remains at their intersection, and then describe the framework proposed by this thesis to close it.


## 1.1 Agentic Benchmarks and the Reliability Problem

The recent surge of interest in LLM-based agents has produced a wave of benchmarks intended to approximate real operational settings. AgentBench [@liu2023] evaluates models across eight diverse environments including web browsing, database manipulation, and operating-system interaction. GAIA [@mialon2023] tests general-purpose assistant capabilities requiring multi-step reasoning and tool use. SWE-bench [@jimenez2024] focuses on autonomous software engineering tasks grounded in real GitHub issues. In the customer-service domain specifically, CRMArena [@huang2025crmarena] and its successor CRMArena-Pro [@huang2025crmarenapro] operationalize CRM workflows into measurable tasks, while API-Bank [@li2023] and ToolLLM [@qin2023] stress-test tool selection and invocation at scale.

Among these, the τ-bench family [@yao2024; @barres2025] is particularly relevant because it operationalizes the full "tool–agent–user" interaction loop into a binary pass/fail criterion. In τ²-bench, a simulated user reveals information incrementally across turns while the agent must follow domain-specific policies, call the correct tools with correct parameters, and modify database state accordingly. The benchmark spans three domains—airline, retail, and telecom—with 50 to 114 tasks each, and its evaluation is strict: a task passes only when every sub-criterion in the reward rubric scores 1.0. Published results underscore an uncomfortable reality: even strong frontier models remain inconsistent across runs and can fail on relatively ordinary multi-step tasks [@barres2025]. A model scoring 85% on the retail domain does not make 15% "small" errors; it fails outright on 15% of customer interactions, each of which represents a broken experience. At enterprise volumes, even a 2% failure rate translates to tens of thousands of mishandled cases per month.

@rabanser2025 formalize this concern under the term *agent reliability*, arguing that accuracy improves faster than reliability across model generations, and that achieving three-to-five nines of reliability requires fundamentally different strategies than those used to improve average-case performance. @kapoor2024 reinforce this point by demonstrating that many published agent evaluations are not robust to variance in prompting, tool ordering, and random seeds, suggesting that headline benchmark numbers may overstate the consistency that enterprises need. These findings establish the demand side of the problem: organizations can tolerate an agent that is impressive in demos, but they will not tolerate one that fails unpredictably in production.


## 1.2 Prompt Engineering, Tool Use, and Static Improvement

In response to unreliable agent behavior, the literature on prompting and tool use has largely focused on making agents more capable in a *static* sense—equipping them with better scaffolds before deployment, rather than enabling them to improve after it.

Chain-of-thought prompting [@wei2022] demonstrated that eliciting intermediate reasoning steps substantially improves multi-step problem solving. ReAct [@yao2023react] extended this insight to agentic settings by interleaving explicit reasoning ("thought") with environment actions ("act"), producing agents that ground their decisions in observed tool outputs rather than hallucinating plans. Tree of Thoughts [@yao2023tot] and Reflexion [@shinn2023] pushed further, allowing agents to explore multiple reasoning paths or reflect on prior failures within a single episode. On the tool-use side, function calling [@openai2023] introduced structured output constraints that dramatically reduce formatting errors by channeling model outputs through predefined JSON schemas. Toolformer [@schick2023] showed that models can learn to invoke tools autonomously during generation, and Gorilla [@patil2023] demonstrated retrieval-augmented tool selection across thousands of APIs. Constrained decoding techniques [@willard2023] further guarantee syntactic validity of tool calls at inference time.

These advances are valuable, but they share a common limitation: once the prompt, schema, and scaffold are fixed, the agent's behavior is static. When a ReAct agent fails to enforce a cancellation policy, the failure persists until a human identifies the root cause, writes a corrective prompt patch, and verifies that the patch does not break other tasks. This remediation cycle is slow, expensive, and does not scale across the hundreds of policy rules that a real customer-service operation maintains.


## 1.3 Alignment, RLHF, and the Enterprise Adaptation Problem

A second line of work addresses the question of shaping model behavior through human feedback. Reinforcement learning from human feedback (RLHF) demonstrated that models can be aligned with human preferences at training time by learning a reward model from pairwise comparisons and then fine-tuning the policy accordingly [@ouyang2022]. Direct Preference Optimization [@rafailov2023] simplifies this pipeline by eliminating the explicit reward model, while Constitutional AI [@bai2022] replaces human annotators with a set of principles that the model uses to critique and revise its own outputs. These methods have been instrumental in making general-purpose models safe and helpful.

However, alignment techniques are not designed to absorb enterprise-specific behavior quickly. RLHF requires large-scale preference collection, training infrastructure, and careful management of reward hacking and alignment tax—the degradation of base capabilities that can accompany alignment tuning [@lin2024; @young2026; @casper2023]. Even parameter-efficient alternatives such as LoRA [@hu2022] require access to model weights, which is unavailable for proprietary API-served models, and they still demand non-trivial data curation and training cycles. For an enterprise that discovers on a Friday afternoon that its agent is mishandling a newly introduced baggage policy, none of these methods offer a same-day fix.

Human-in-the-loop (HITL) customer-service systems exist, but they primarily use humans as real-time supervisors who correct agent outputs in the moment rather than as a source of reusable learning signals that update the agent's logic for future encounters. The human resolves the immediate case but the agent does not retain the lesson. This makes HITL architectures expensive to operate indefinitely and prevents the kind of progressive improvement that would eventually reduce the human's workload.


## 1.4 Automated Prompt Optimization: Progress and Blind Spots

A newer body of work attempts to automate the prompt engineering loop itself. APE [@zhou2022] showed that LLMs can generate and score candidate prompts, effectively serving as their own prompt engineers. OPRO [@yang2023] framed prompt optimization as a meta-optimization problem, iteratively refining instructions using the model's own evaluative capacity. DSPy [@khattab2023] introduced a programming framework that compiles declarative LLM pipelines into optimized prompt chains. TextGrad [@yuksekgonul2024] proposed treating natural-language feedback as a gradient signal, propagating textual critiques backward through multi-step LLM computations to improve each component. Trace [@cheng2024] extended this metaphor to execution traces, using rich feedback from program execution to guide optimization. PromptBreeder [@fernando2023] and EvoPrompt [@guo2023] applied evolutionary strategies, mutating and selecting prompts over multiple generations.

Most recently, GEPA [@agrawal2025] achieved strong results by combining reflective analysis of failure traces with iterative prompt evolution, demonstrating at ICLR 2026 that this approach can outperform reinforcement learning on reasoning and classification tasks. SCOPE [@pei2025] explored self-evolving context optimization, and AgentOptimizer [@zhang2024] treated agent functions as learnable weights that can be tuned offline through textual gradients.

On the tool-description side, PLAY2PROMPT [@fang2025] introduced zero-shot tool instruction optimization through simulated tool interactions, and @guo2026 proposed learning to rewrite tool descriptions for more reliable LLM-agent tool use. AvaTaR [@wu2024] optimized LLM agents specifically for tool-assisted knowledge retrieval.

Despite this rapid progress, a critical blind spot remains. **Automated prompt optimization has not been validated on multi-turn, tool-calling agent benchmarks.** GEPA, the closest methodological precedent, was evaluated on reasoning tasks (GSM8K, MATH) and classification benchmarks—settings where the agent produces a single output per input and does not maintain state across turns. DSPy similarly targets single-turn or short-chain pipelines. TextGrad's demonstrations involve question answering and code generation, not stateful, policy-governed conversations that unfold over 10-20 turns with interleaved tool calls. No existing work has demonstrated automated prompt evolution on a benchmark like τ²-bench, where the agent must simultaneously manage dialogue state, enforce multi-clause policies, and invoke tools with exact parameters across a sustained interaction.


## 1.5 Knowledge Distillation: Weights but Not Prompts

A parallel literature on knowledge distillation offers another angle on the problem of transferring capability from stronger to weaker models. @hinton2015 established the foundational framework of training a smaller "student" network to mimic the soft outputs of a larger "teacher." In the LLM era, this idea has been adapted through instruction-tuning distillation: Alpaca [@taori2023], Vicuna [@chiang2023], and WizardLM [@xu2023wizard] all trained smaller models on outputs generated by larger ones, while Lion [@jiang2023] introduced adversarial distillation to improve the transfer. Self-Instruct [@wang2023] showed that models can generate their own training data for instruction following. TinyBERT [@jiao2020] and DistilBERT [@sanh2019] demonstrated that significant compression is possible with minimal performance loss.

However, all of these approaches operate at the weight level: the student's parameters are modified through gradient-based training. This requires access to model internals, training infrastructure, and non-trivial compute. For organizations using API-served models—increasingly the norm as frontier capabilities concentrate in a handful of providers—weight-level distillation is simply not available. The question of whether a teacher model can transfer knowledge to a student *at the prompt level*, by diagnosing the student's failures and editing its operating instructions, has not been empirically investigated in the context of tool-using agents. @choudhury2024 explored LLM agents learning from privileged AI feedback, and @shenfeld2026 demonstrated self-distillation for continual learning, but neither addresses the specific setting of prompt-level transfer for multi-turn tool calling.


## 1.6 The Gap

The preceding review reveals a clear gap at the intersection of four research streams. Agentic benchmarks have established *where* LLM agents fail and quantified the reliability deficit that blocks enterprise adoption. Prompt and tool engineering have improved *static* agent capability but offer no mechanism for post-deployment learning. Alignment techniques can shape model behavior but are too heavyweight for rapid, enterprise-specific iteration. Automated prompt optimization has demonstrated that LLMs can improve their own instructions, but has not been tested on the class of benchmarks that most closely approximates real customer-service operations.

What is missing is an empirical workflow that (a) uses a stronger teacher model to diagnose failures in a weaker student's conversation traces, (b) converts those diagnoses into structured edits to the student's prompts, tool schemas, and tool preprocessing logic, (c) validates each edit against the benchmark to prevent regressions, and (d) demonstrates repeatable improvement on a multi-turn, tool-calling benchmark—all without modifying any model weights.

This gap matters because it is exactly where enterprise adoption stalls. Organizations need agents that improve continuously from operational experience, that can absorb new policies without retraining, and that can be audited and rolled back when changes cause regressions. Weight-level approaches cannot provide this. Manual prompt engineering cannot scale to provide this. The gap is not merely academic; it represents a concrete barrier to the deployment of AI agents in domains where reliability is a business requirement.


## 1.7 Research Question and Objectives

This thesis asks: **How can AI agent performance on structured benchmarks be improved through automated, teacher-model-driven prompt and tool evolution?**

Three sub-questions guide the investigation:

1. Which failure modes in multi-turn tool-calling tasks are most responsive to prompt and tool-schema edits, and which resist them?
2. What is the scaling behavior of the evolution framework—does fix rate hold as the task pool grows, or does it degrade?
3. Can prompt-level patches generated by a teacher model close a meaningful fraction of the performance gap between a weak student and a frontier ceiling, without any weight updates?

To answer these questions, the thesis pursues the following objectives:

1. Run a baseline evaluation of a small open-source model (Qwen3 30B-A3B with 3.3B active parameters) on the τ²-bench airline domain and categorize its failure modes.
2. Design a diagnose-patch-validate loop in which a stronger teacher model (Kimi K2.5) analyzes failed conversation traces, proposes patches across three surfaces (system prompt, tool schemas, and tool preprocessors), and validates each patch through re-simulation.
3. Implement the framework in Python and evaluate it across increasing task-pool sizes (5, 10, and 20 tasks) to characterize scaling behavior.
4. Measure gap closure—the fraction of the baseline-to-frontier performance gap that prompt-level evolution can recover—as the primary outcome metric.
5. Analyze the distribution of successful and unsuccessful patches to identify the boundaries of what prompt-level intervention can and cannot fix.


## 1.8 Contributions

This thesis makes the following contributions:

First, it introduces a teacher-driven prompt evolution framework that operates entirely in the input space of a frozen student model. The framework uses a diagnose-patch-validate loop with three patch surfaces—prompt insertions, tool-schema edits, and sandboxed tool preprocessors—and enforces unanimous validation before merging any patch. This design is compatible with API-only model access and produces auditable, versionable, rollback-able changes.

Second, it provides the first empirical evaluation of automated prompt optimization on a multi-turn, tool-calling benchmark (τ²-bench). Prior work on automated prompt evolution has targeted single-turn reasoning and classification tasks; this thesis extends the paradigm to stateful, policy-governed agent interactions.

Third, it contributes empirical evidence on the scaling behavior of prompt-level evolution. The experiments reveal a stable absolute improvement of approximately 20 percentage points in trial pass rate, a declining fix rate as harder tasks dilute the pool, and the emergence of a "hard core" of resistant tasks that likely require capabilities beyond what prompt editing can provide.

Fourth, the findings provide indirect support for the Superficial Alignment Hypothesis [@zhou2023lima] in the agentic setting: 71% of successful fixes are simple instruction-level patches that tell the model *what* to do, rather than *how* to do it. The model possesses the capability; the prompt merely needs to activate it.


## 1.9 Thesis Structure

The remainder of this thesis is organized as follows. Chapter 2 presents a detailed literature review covering agentic benchmarks, prompt optimization methods, knowledge distillation, and agent reliability. Chapter 3 describes the research methodology, grounding the work in the design science paradigm [@hevner2004; @peffers2007] and detailing the experimental setup. Chapter 4 presents the framework architecture—the diagnose-patch-validate loop, the three patch surfaces, and the two-phase escalation strategy. Chapter 5 reports the experimental results across three task-pool sizes and two student models. Chapter 6 discusses the findings, their implications for enterprise AI deployment, and the limitations of the approach. Chapter 7 concludes with a summary of contributions and directions for future work.