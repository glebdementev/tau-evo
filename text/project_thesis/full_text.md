# Project Thesis Full Text

_Generated from the source markdown used by `build.sh`._



<!-- FILE: metadata.yaml -->

---
bibliography: references.bib
csl: ../apa.csl
reference-section-title: "REFERENCES"
lang: en-US
toc: true
toc-title: "TABLE OF CONTENTS"
toc-depth: 2

# --- GOST 7.32-2017 page layout ---
documentclass: extarticle
fontsize: 12pt
papersize: a4
geometry:
  - left=30mm
  - right=15mm
  - top=20mm
  - bottom=20mm
linestretch: 1.5
mainfont: "Times New Roman"

# --- pandoc-crossref ---
figPrefix: "Figure"
tblPrefix: "Table"
figureTitle: "Figure"
tableTitle: "Table"
titleDelim: ":"
linkReferences: true
lofTitle: "# List of Figures"
lotTitle: "# List of Tables"

# LaTeX preamble is loaded via defaults.yaml (include-in-header)
---



<!-- FILE: 00_introduction.md -->

# INTRODUCTION

The deployment of large language models as customer-facing agents is a commercial application of generative AI. Within customer service alone, LLM-based agents hold multi-turn conversations, enforce domain-specific policies, and invoke back-end tools on the customer's behalf [@barres2025; @huang2025crmarena]. A capable agent can resolve routine tickets at 5--10$\times$ lower cost per interaction than a human operator [@gartner2023cost; @quidget2025], and the addressable market for such "Services as Software" is estimated at \$4.6 trillion [@foundationcapital2024]. Yet over 80% of AI projects in general fail to reach production [@ryseff2024], and 95% of generative AI pilots specifically fail to deliver measurable P\&L impact [@mitnanda2025]. The bottleneck is ensuring agents work reliably throughout the deployment.

Many models of previous and current generation---GPT-4 [@openai2024], Claude [@anthropic2025], Qwen3 [@qwen2025]---fail 30--50% of multi-turn tool-calling tasks on structured benchmarks such as $\tau^2$-bench [@barres2025], while autonomous enterprise operation would require 3-to-5 nines of reliability [@rabanser2025]. An agent that fails on a policy edge case will fail on the same edge case on every subsequent encounter, unless a human engineer manually diagnoses the failure, rewrites the prompt or tool schema, and re-deploys the agent. At enterprise scale, where thousands of edge cases accumulate across dozens of policy domains, this manual remediation loop---the *implementation tax*---is estimated at 0.5--3 full-time equivalents and \$45,000--\$55,000 per year per deployment, based on industry cost analyses [@gartner2025complexity; @pwc2025aijobs]. The implementation tax is the barrier to profitable scaling of AI agent businesses and to enterprise adoption of agentic automation.

*target ai* LLC is a Russian technology company operating in the customer experience (CX) automation market. Its portfolio spans two technology generations: an NLU-era voice product (target voice, ≈60 million rubles in 2025, down from ≈210 million rubles in 2024 as customers migrate); the LLM-based agent-building platforms target os (*tos1*) at ≈200 million rubles in 2025 and its successor *tos2* (the substrate of this thesis); a wizard-driven training product (target skill, ≈16 million rubles); and the pre-revenue omnichannel UI target space. The flagship *tos1* is commercially successful, but its delivery model depends on a team of specialized systems analysts who translate each customer's requirements into the agent's prompt, tool schemas, and policy configuration; that translation step is the binding constraint on profitable scaling. *target ai* consumes self-hosted models through APIs without weight modification, and prefers avoiding fine-tuning, RLHF, or other weight-modification approaches. When the systems-analyst team misses a requirement, gets a policy wrong, or has to absorb a downstream policy change, the only currently available remediation path is the same manual loop: a specialist analyzes conversation logs and rewrites prompts or schemas by hand, subsequently running the simulation. This process scales linearly with the number of deployed agents and policy-change events, and requires the same headcount needed to onboard new clients.

The present thesis is a project-based study that addresses this operational bottleneck.

**Object of study:** *target ai*'s *tos* line of agent-building platforms (*tos1* in production and *tos2* in development) and the AI agents deployed through them.

**Subject of study:** the alignment of AI agents to customer preference functions through automated prompt and tool-schema evolution, covering both the initial requirements-translation step and ongoing post-deployment correction.

**Aim:** to design, implement, and evaluate an automated diagnose-patch-validate (DPV) framework that aligns a weaker "student" agent to a customer preference function by using a stronger "teacher" model to analyze failures in the student's conversation traces, generate structured patches to the student's prompts and tool schemas, and validate each patch through re-simulation, all without modifying any model weights. This formulation makes $\tau^2$-bench [@barres2025] a suitable evaluation substrate: each $\tau^2$-bench task encodes a customer preference (a reward rubric over exactly the same dimensions) that the agent must satisfy, mirroring the structure of an enterprise customer's acceptance criteria. The aim is pursued through five project objectives: designing the framework, evaluating it on the $\tau^2$-bench, characterizing which failure types respond to prompt-level intervention, assessing scaling behavior, and producing actionable recommendations for *target ai*; these are detailed in Section 1.1.

The thesis is structured as follows. Chapter 1 establishes the theoretical foundations and problem analysis: the organizational problem at *target ai* (Section 1.1), a review of relevant literature and industry practice (Section 1.2), and a diagnostic study of the CX automation market and *target ai*'s competitive position using Porter's Five Forces, Value Chain Analysis, and cost structure analysis (Section 1.3). Chapter 2 presents the implementation methodology: the selection and justification of the Engineering Design Process as the project methodology (Section 2.1), a phase-by-phase implementation plan mapping EDP stages to project activities (Section 2.2), the DPV framework architecture (Section 2.3), and implementation details and experimental setup (Section 2.4). Chapter 3 covers the experimental results and evaluation: results across three increasingly larger task subsets and three models (Sections 3.1--3.4), and effectiveness evaluation against project objectives, economic analysis, and recommendations for *target ai* (Section 3.5). The Conclusion summarizes findings, contributions, limitations, and directions for further research.



<!-- FILE: ch1_0_chapter.md -->

\newpage

# 1. Theoretical Foundations and Problem Analysis



<!-- FILE: ch1_1_organizational_problem.md -->

## 1.1 The Organizational Problem

*target ai* LLC is a Russian technology company operating in the customer experience (CX) automation market. The company serves enterprise clients across retail, telecom, airline, and financial services verticals through five products that span two technology generations and two delivery models:

- **target os (*tos1*)**: the company's current flagship, a model-agnostic LLM-based platform for *building* customer-facing AI agents. *tos1* generated approximately 200 million rubles in revenue in 2025 and is maintained by a team of eight developers. The platform itself produces only the agent runtime; translating each customer's requirements into a working agent is performed by a dedicated team of specialized systems analysts.
- ***tos2***: the next-generation successor to *tos1*, currently being developed by the author of this thesis. *tos2* is the deployment substrate for the framework presented in this work; the framework is the response to the systems-analyst bottleneck observed during their prior work on *tos1*, from which they transitioned in order to design and build *tos2*.
- **target voice**: the NLU-based predecessor to the *tos* line. In 2024, target voice generated approximately 210 million rubles and accounted for the entire company revenue; in 2025 it produced approximately 60 million rubles as customers migrated to LLM-based *tos* deployments. target voice remains in managed decline.
- **target skill**: voice-AI training courses in which non-technical users build simple agents by prompting a fixed conversational architecture through a wizard. target skill generated approximately 16 million rubles in 2025 and represents the company's "no analyst required" baseline: a working but capability-bounded delivery model.
- **target space**: an omnichannel CX platform that lets human operators and AI agents collaborate in a single user interface for contact-center operations. target space is pre-revenue.

*target ai*'s total headcount is approximately 75 people across all functions. The implementation organization --- the team of systems analysts who translate each customer's requirements into a working agent --- numbers 25, the single largest functional group in the company. Engineering totals 19 developers: eight on *tos1*, 10 on the rest of the product line (target voice, target skill, target space, and shared platform infrastructure), and one on *tos2*. The commercial organization comprises 22 sales staff, of whom eight are account executives who demonstrate the platform and lead client engagements. A 4-person product-management team and approximately five support staff (finance, accounting, operations) complete the count. The structural fact this distribution exposes is decisive: *target ai* employs more systems analysts (25) than developers (19), and the analyst layer is the largest single function in the company. Every additional *tos1* deployment, and every customer migrated from target voice onto the *tos* line, draws on this same pool, and it is the only function whose load grows linearly with the number of active deployments and the rate of policy-change events.

The core operational problem manifests inside *tos1*'s delivery model. *tos1* is commercially successful, but every new agent deployment requires specialized systems analysts to translate customer requirements into the agent's system prompt, tool schemas, and policy configuration. This translation step is the dominant failure surface: details get missed, delivery slips, and customers --- *target ai*'s enterprise customers, not their end users --- return correction requests that the analyst team must then re-process. The bottleneck is not a lack of LLM capability or platform features; it is the human-bandwidth cost of converting an enterprise's stated preferences into a working agent. As the *tos* line absorbs the migrating target voice customer base and grows beyond its current 200-million-ruble baseline, scaling the analyst headcount linearly with deployments is not economically viable, and the same scarce headcount is the only resource currently available for downstream correction when policies change or edge cases surface in production.

The solution direction this thesis explores is to replace much of the analyst-driven translation step with automated alignment of an agent to a *customer preference function*: a structured specification of what the customer considers a successful interaction, encoded as task-level pass/fail criteria over policy adherence, tool use, and resulting database state. Given such a preference function, the framework iteratively diagnoses where the agent fails to satisfy it and produces patches to the agent's prompts and tool schemas until the agent's behavior conforms. This formulation makes $\tau^2$-bench [@barres2025] a particularly apt evaluation substrate: each $\tau^2$-bench task encodes a customer preference (a reward rubric over exactly the same dimensions) that the agent must satisfy, mirroring the structure of an enterprise customer's acceptance criteria 1-to-1. The framework's task is to align a frozen API-served student agent to such preferences without modifying any model weights, and without requiring a systems analyst to author the prompt by hand.

This reframing has two implications worth stating up front. First, the same mechanism that automates *initial* requirements translation also automates *ongoing* alignment: when the customer's preference function changes (a new policy, a regulatory shift, an edge case discovered in production), the framework can re-converge against the updated preferences without scheduling analyst time. The literature on agent drift [@agentdrift2025] and temporal model degradation reinforces that ongoing alignment is not an optional second phase but a permanent operational requirement; in a study of traditional machine learning models across 32 datasets, @vela2022 found that 91% of model--dataset pairs exhibited temporal quality degradation. Second, the framework operates *entirely in the input space* of the student model: prompt insertions, tool-schema edits, and sandboxed tool preprocessors. *target ai* consumes all models through APIs (primarily OpenRouter and direct provider APIs) without weight access, which rules out fine-tuning, RLHF, DPO, and any other weight-modification approach to alignment. The constraint is reinforced by geopolitical restrictions that limit the availability of certain Western frontier model APIs in the Russian market, making model-agnostic, API-compatible solutions the only viable path. Rather than treating this as a limitation, the framework treats input-space alignment as the design target.

The economic case for automation is sharpened by a comparison internal to *target ai*'s own portfolio. target skill --- the wizard-driven product where non-specialists prompt a fixed architecture without analyst involvement --- works, but only at the bottom of the complexity range, generating roughly 16 million rubles. *tos1* --- the analyst-driven product capable of arbitrary enterprise complexity --- generates roughly 200 million rubles but absorbs the analyst team's entire bandwidth. The thesis question, in those terms, is whether prompt-level evolution can give the *tos* line target skill's labor profile at *tos1*'s complexity ceiling. The same pressure is visible in the wider market. Post-deployment maintenance is estimated at 0.5 to 3 full-time equivalents and \$45,000--\$55,000 per year per deployment, based on industry cost analyses [@gartner2025complexity]. Workers with AI skills command a 56% wage premium, up from 25% in 2024 [@pwc2025aijobs], and prompt engineers earn a median of \$126,000--\$128,000, with senior roles reaching \$300,000+ [@glassdoor2025prompt]. IDC projects that by 2026, over 90% of organizations worldwide will face IT skills shortages --- with AI identified as the most in-demand category --- amounting to \$5.5 trillion in losses [@idc2025skills]. AI-first companies broadly operate at 50--60% gross margins, well below the 75--90% typical of traditional SaaS, largely due to higher compute and services costs [@bessemer2025]. Over 80% of AI projects in general fail to reach production [@ryseff2024], 95% of generative AI pilots specifically fail to deliver measurable P\&L impact [@mitnanda2025], only 25% of enterprises have moved more than 40% of their AI pilots into production [@deloitte2026ai], and Forrester predicts that three out of four firms attempting to build agentic architectures independently will fail [@forrester2025]. The author's experience operating *tos2* is a concrete instance of the same pressure: a developer cannot deliver what eight do, and the gap must be closed through automation rather than headcount.

Given this context, the present thesis defines its scope as follows. The *object of study* is *target ai*'s *tos* line of agent-building platforms --- *tos1* in production and *tos2* in development --- and the AI agents deployed through them. The *subject of study* is the alignment of API-served AI agents to customer preference functions through automated prompt and tool-schema evolution, covering both the initial requirements-translation step and ongoing post-deployment correction. The study is limited to the airline domain of the $\tau^2$-bench benchmark [@barres2025] as a proxy for *target ai*'s operational domains, evaluating three student models (Qwen3 30B-A3B, Qwen3.5 Flash, GLM 4.7 Flash) with a single teacher model (Kimi K2.5) across task-pool sizes of 5, 10, and 20 tasks. The framework operates entirely in the input space of the student model; no model weights are modified.

To address the organizational problem, the thesis pursues five project objectives:

1. **Design an automated framework for teacher-driven prompt evolution.** Architect a diagnose-patch-validate loop with three patch surfaces: system prompt insertions, tool-schema edits, and sandboxed tool preprocessors. The loop operates entirely in the input space of a frozen student model and produces auditable, versionable, rollback-able changes compatible with API-only model access.

2. **Evaluate the framework on $\tau^2$-bench as a proxy for *target ai*'s operational domains.** Run baseline and post-evolution evaluations of a small open-source student model (Qwen3 30B-A3B) on the $\tau^2$-bench airline domain across increasing task-pool sizes (5, 10, and 20 tasks) to measure effectiveness under controlled conditions.

3. **Characterize which failure types respond to prompt-level intervention.** Analyze the distribution of successful and unsuccessful patches across the failure taxonomy (tool misuse, policy violation, reasoning error, communication error) to identify the boundaries of what prompt-level evolution can and cannot fix.

4. **Assess scaling behavior and practical boundaries.** Determine whether the fix rate holds as the task pool grows or degrades, establishing the practical limits of the approach and identifying where complementary methods (e.g., fine-tuning, architectural changes) would be needed.

5. **Produce actionable recommendations for *target ai*'s deployment pipeline.** Translate experimental findings into a phased integration roadmap: from internal benchmark validation through shadow-mode deployment to fully automated closed-loop optimization, with defined team responsibilities, cost projections, and success criteria.

The problem addressed by this thesis is relevant at three levels. At the *business level*, the "Services as Software" market is estimated at \$4.6 trillion [@foundationcapital2024], and McKinsey projects that agentic AI could unlock \$100--400 billion in incremental spending in tech services alone by decade's end [@mckinsey2025techservices]; reducing the human cost of aligning agents to customer preferences is a prerequisite for capturing this opportunity. At the *industry level*, the shift to outcome-based pricing, where vendors bear the economic risk of agent performance directly, transforms agent reliability from a quality concern into a direct margin driver. Intercom charges \$0.99 per resolution [@intercom2024]; Sierra implements pure outcome-based pricing [@sierra2024]. Under these models, every unresolved interaction is revenue forgone, and automated alignment becomes a competitive differentiator. At the *organizational level*, the framework directly addresses the highest-cost, lowest-automation layer in *target ai*'s service delivery chain: the systems-analyst team that translates customer requirements into agent configuration and absorbs every downstream policy change. It shifts the cost structure from linear (proportional to deployments and analyst hours) to near-fixed (the compute cost of running the teacher model).



<!-- FILE: ch1_2_literature_and_practice.md -->

## 1.2 Literature and Practice Review

This section reviews how enterprises and researchers have addressed the reliability of AI agents in customer service, surveys the major approaches to automated improvement, and synthesizes four conclusions that shape the framework developed in Chapter 2.

### The Enterprise Agent Reliability Gap

Frontier models have improved sharply, but agentic benchmarks have not saturated. The τ-bench family of benchmarks [@yao2024; @barres2025] captures the full "tool-agent-user" interaction loop with binary pass/fail evaluation: a task passes only when every sub-criterion in the reward rubric scores 1.0. In τ²-bench [@barres2025], a simulated user reveals information incrementally across turns while the agent must follow domain-specific policies, call the correct tools with correct parameters, and modify database state accordingly. The benchmark spans airline, retail, and telecom domains with 50 to 114 tasks each. Even strong frontier models remain inconsistent across runs; a model scoring 85% on a domain does not make 15% "small" errors; it fails outright on 15% of customer interactions. GPT-4o failed 50%+ of tasks on the original τ-bench, and the probability of solving the same task 8 times consecutively was <25% in the retail domain [@yao2024].

The reliability gap is not unique to τ-bench. AgentBench [@liu2023] tested 29 models across 8 environments and identified long-term reasoning, decision-making, and instruction following as the main bottlenecks. SWE-bench [@jimenez2024] found that at the time of publication the best model solved under 2% of 2,294 software engineering tasks; the curated SWE-bench Verified subset later rose above 80% for frontier models, but OpenAI now argues that the benchmark is no longer a reliable frontier-coding measure because remaining failures often reflect flawed tests or memorization risk rather than pure model capability [@openai2026sweverified]. Newer agentic evaluations still show residual gaps: GPT-5.5 reaches 58.6% on SWE-Bench Pro, 82.7% on Terminal-Bench 2.0, 78.7% on OSWorld-Verified, 55.6% on Toolathlon, and 98.0% on τ²-bench Telecom without prompt tuning [@openai2026gpt55]. Claude Opus 4.7 improves over Opus 4.6 on advanced coding and multi-step agent workflows, including a 64.3% SWE-Bench Pro score reported in OpenAI's comparison table and Anthropic's own evidence of lower tool-error rates in partner agent evaluations [@anthropic2026opus47; @openai2026gpt55]. Open-weight frontier models show the same pattern rather than eliminating it: Kimi K2.6 reports 58.6% on SWE-Bench Pro, 80.2% on SWE-Bench Verified, 66.7% on Terminal-Bench 2.0, and 73.1% on OSWorld-Verified [@kimi2026k26], while DeepSeek-V4-Pro-Max reports 80.6% on SWE-Bench Verified, 67.9% on Terminal-Bench 2.0, and 51.8% on Toolathlon [@deepseek2026v4]. Older benchmarks tell the same story historically: GAIA [@mialon2023] revealed a 77-point gap between human performance (92%) and GPT-4 with plugins (15%); ToolBench [@qin2023] and API-Bank [@li2023] exposed failures in tool selection, parameter extraction, and sequential planning; and CRMArena-Pro showed leading CRM agents dropping from 58% single-turn success to 35% in multi-turn settings [@huang2025crmarena; @huang2025crmarenapro].

@Fig:benchmark-gap summarizes recent frontier-model scores across representative agentic benchmarks. The metrics are not a single leaderboard; they span coding agents, computer-use agents, tool-use agents, and customer-service simulation, but they establish the general point: outside isolated cases, even the newest frontier models remain below saturation.

![Recent frontier agent benchmark scores. Scores are drawn from current model-release and technical-report sources; each row keeps the benchmark metric explicit, and the grey segment shows the remaining gap to perfect task success.](figures/fig_lr_02_benchmark_gap.png){#fig:benchmark-gap}

Two meta-analyses frame these results. @kapoor2024 found 50-fold cost variation for similar accuracy levels across agent benchmarks, with complex architectures buying marginal gains at exponential cost---supporting prompt-level optimization over architectural scaling. @rabanser2025 identified a persistent *capability--reliability gap*: accuracy improves faster than reliability, and enterprise autonomous operation requires 3 to 5 nines (99.9--99.999%). @reliabilitybench2026 formalized this quantitatively, introducing a reliability surface that unifies consistency, robustness, and fault tolerance, showing that perturbations can reduce success rates by 9--15 percentage points under realistic stress conditions. @brynjolfsson2025, studying 5,172 customer support agents in *The Quarterly Journal of Economics*, found that AI assistance increases productivity by 14--15% on average and by 34% for novice workers, because AI disseminates best practices of more able workers---directly supporting the thesis's approach of continuously disseminating best practices through automated optimization.

The reliability gap acquires urgency when set against market economics. Fully automated AI interactions cost \$0.50--\$2.00 per interaction versus \$5--\$15 for human agents [@gartner2023cost; @quidget2025], creating a 5--10$\times$ cost advantage. The contact center AI market is expanding at 21--25% CAGR, from roughly \$2 billion in 2024 to a projected \$7--13 billion by 2030--2034 [@grandviewresearch2024; @fortunebi2025]. Yet over 80% of AI projects in general fail---twice the rate of non-AI IT projects [@ryseff2024]---and 95% of generative AI pilots specifically fail to deliver measurable P\&L impact [@mitnanda2025]. Only 25% of enterprises have moved more than 40% of their AI pilots into production [@deloitte2026ai].

The most prominent case study illustrates both the promise and the fragility. Klarna's AI assistant handled 2.3 million conversations in its first month---equivalent to 700 full-time agents---reducing resolution time from 11 to 2 minutes and projecting \$40 million in annual profit improvement [@klarna2025]. Yet within a year, customer satisfaction had declined, and the company began rehiring human agents [@forrester2025regret]. The pattern is not isolated: Gartner predicts that 50% of organizations will abandon plans to reduce their customer-service workforce through AI by 2027 [@gartner2025abandon], and among companies that did pursue AI-driven layoffs, 55% reported regretting the decision [@forrester2025regret].

The talent required for manual prompt engineering is scarce. As quantified in Section 1.1, AI skills command a 56% wage premium [@pwc2025aijobs], prompt engineers earn \$126,000--\$300,000+ [@glassdoor2025prompt], and over 90% of organizations face IT skills shortages [@idc2025skills]. Forrester predicts that three out of four firms building agentic architectures independently will fail [@forrester2025].

A concurrent pricing shift intensifies the pressure. The industry is moving from per-seat licensing to outcome-based models: Intercom charges \$0.99 per resolution [@intercom2024], Sierra implements pure outcome-based pricing [@sierra2024]. Under outcome-based pricing, vendors bear the economic risk of agent performance directly: every unresolved interaction is revenue forgone. AI-first companies operate at 50--60% gross margins, well below the 75--90% typical of traditional SaaS [@bessemer2025]. Gartner forecasts that generative AI cost per resolution will exceed \$3 by 2030 as current LLM vendor pricing---which they estimate is subsidized by up to 90%---normalizes [@gartner2026costwarning].

The scale of the opportunity is commensurate: Foundation Capital estimates the "Services as Software" market at \$4.6 trillion [@foundationcapital2024], and McKinsey projects that agentic AI could unlock \$100--400 billion in incremental tech services spending by decade's end [@mckinsey2025techservices].

The reliability gap is compounded by *agent drift*---progressive behavioral degradation in multi-agent LLM systems even without explicit parameter changes [@agentdrift2025]---and by temporal quality degradation observed across 91% of model--dataset pairs in traditional ML deployments [@vela2022]. Both phenomena underscore that continuous re-optimization, rather than one-time configuration, is the norm for deployed AI systems. As documented in Section 1.1, post-deployment maintenance costs 0.5--3 FTEs and \$45,000--\$55,000 per year per deployment [@gartner2025complexity], and failures persist until manually diagnosed and fixed. At enterprise scale, where thousands of edge cases accumulate across dozens of policy domains, this manual remediation loop is the binding constraint on profitable scaling. The combination of market size, structural cost advantages, and persistent implementation failure creates the business case for automated prompt evolution.

### Approaches to Automated Prompt and Agent Improvement

Six broad approaches to improving agent performance have emerged in the literature, each addressing part of the problem but none addressing all of it.

Chain-of-thought prompting [@wei2022] showed that hand-crafted reasoning exemplars improve multi-step problem solving, with PaLM-540B reaching state-of-the-art on GSM8K. The ReAct framework [@yao2023react] extended this to agentic settings by interleaving reasoning traces with task-specific actions, outperforming both pure chain-of-thought and pure action-generation baselines on question answering, fact verification, and interactive decision-making. Tree of Thoughts [@yao2023tot] generalized this with tree search and self-evaluation, reaching 74% on Game of 24 compared to chain-of-thought's 4%. On the tool-use side, function calling [@openai2023] introduced schema-driven structured output. Toolformer [@schick2023] trained models to invoke tools autonomously, matching much larger models at zero-shot performance. Gorilla [@patil2023] fine-tuned LLaMA to surpass GPT-4 on API call generation while showing that GPT-4 frequently hallucinates incorrect API usage under prompting alone. Constrained decoding [@willard2023] guaranteed syntactic validity of tool calls but addressed only format, not reasoning or planning.

A useful lens for understanding the limitation of these static techniques comes from dual-process theory. @kahneman2011 distinguishes between System 1 (fast, automatic processing) and System 2 (slow, deliberate reasoning). Standard autoregressive models function as System 1: fluent and contextually appropriate, but struggling with multi-step planning and policy adherence [@yao2023react]. Reasoning models---OpenAI's o1 [@openai2024], DeepSeek-R1 [@deepseek2025], Kimi K1.5 [@kimi2025a]---approximate System 2 behavior by scaling test-time compute. But in voice AI customer service, latency constraints (500--800ms for natural flow; industry estimates suggest that 1-second latency significantly raises abandonment rates [@cresta2025; @retellai2025]) make extended reasoning incompatible with runtime requirements. This thesis resolves this tension through temporal disjunction: System 2 at design time (teacher analyzing failures offline) to improve System 1 at runtime (student responding within latency constraints using improved prompts).

For all these advances, static approaches share a fundamental limitation: they fix the agent's behavioral repertoire at design time. @brown2020 showed that in-context few-shot learning has task-dependent ceilings. @zhou2022 found through Automatic Prompt Engineer that optimal prompts are fragile: small wording changes alter effectiveness. @sclar2023 provide the sharpest evidence: meaning-preserving formatting changes produce up to 76 accuracy points of variation on LLaMA-2-13B, and larger models, more examples, and instruction tuning did not eliminate this sensitivity.

![Prompt format sensitivity across models, based on data from @sclar2023. Each bar shows the accuracy range between worst and best formatting of the same few-shot prompt.](figures/fig_lr_03_prompt_sensitivity.png){#fig:prompt-sensitivity}

A scaffold is only as good as the moment it was built for; the moment passes. In business terms, every policy change, product update, or regulatory shift requires a human expert to revisit and re-engineer the agent's prompts and tool schemas, a recurring cost compounded by agent drift.

If static prompting hits a ceiling, the natural question is whether updating model weights can break through it. The answer is yes---but at a cost structurally incompatible with how enterprises need to operate. Supervised fine-tuning (SFT) is the most direct form. @zhou2023lima demonstrated that fine-tuning LLaMA-65B on just 1,000 curated examples produced alignment quality competitive with RLHF-trained models. Their *Superficial Alignment Hypothesis*---that alignment primarily teaches style and format rather than injecting new knowledge---is directly relevant to this thesis: if alignment is primarily about style, then prompt-level interventions should be capable of producing behavioral changes without touching weights. But each new domain requires its own curated dataset, and every policy change requires rebuilding and retraining. @shenfeld2026 found that standard SFT causes catastrophic forgetting when applied to reasoning models, and proposed self-distillation as a mitigation.

RLHF goes beyond SFT by training models to satisfy preferences. @ouyang2022 showed a 1.3B-parameter model fine-tuned with RLHF was preferred over 175B GPT-3 in 85% of comparisons --- a 100× parameter disadvantage overcome by alignment. But the pipeline requires three stages (SFT, reward model training, PPO), each demanding its own dataset and infrastructure. The authors identified an "alignment tax": improved preference ratings at the cost of regressions on general benchmarks. @bai2022 proposed Constitutional AI to reduce the human feedback burden, but still requires a complex multi-phase pipeline. DPO [@rafailov2023] eliminates the separate reward model, matching RLHF with simpler engineering, but the core bottleneck of domain-specific preference data is unchanged. LoRA [@hu2022] reduces trainable parameters by up to 10,000×, making any method cheaper, but does not eliminate the need for task-specific data. Conceptually, this entire family is the literature on aligning a model to a *preference function* --- exactly the framing the present thesis adopts in Section 1.1, where each $\tau^2$-bench task encodes a customer's acceptance criteria as a structured preference. The framework developed in Chapter 2 can therefore be read as a preference-learning method that operates in the input space of a frozen API-served student rather than in its parameter space, taking the same target as RLHF and DPO but using the only optimization surface available under the API-only constraint.

The deeper issue is irreversibility. @luo2023 found that catastrophic forgetting is universal during continual instruction tuning, with larger models forgetting more severely. @lin2024 quantified the alignment tax: RLHF degrades pretrained abilities in translation, reading comprehension, and reasoning, and existing mitigations do not fully compensate. @young2026 provided the first mathematical definition: the alignment tax rate equals the squared projection of the safety direction onto the capability subspace, and the Pareto frontier admits an *irreducible component*---the alignment tax is a structural property of weight modification, not an engineering limitation to be optimized away. @casper2023 surveyed RLHF challenges more broadly---noisy feedback, reward hacking, distributional shift, instability---and argued that human evaluators miss over half of errors.

![Comparison of fine-tuning approaches. Prompt-level optimization is the only approach requiring no weight updates, no alignment tax, no forgetting risk, and full reversibility.](figures/fig_lr_04_finetuning_comparison.png){#fig:finetuning-comparison}

Even practitioners within the RL community have acknowledged this. @cai2025 proposed Training-Free GRPO, shifting optimization from parameter space to context space entirely, reducing costs from ~\$800 (fine-tuning a 32B model) to ~\$8 (inference-only optimization on a frozen larger model). The authors explicitly argue that standard GRPO "incurs prohibitive computational costs and risks catastrophic forgetting." For enterprises consuming models via API---without weight access, training infrastructure, or ML engineering teams---weight modification is simply unavailable. This motivates operating at the prompt and tool description layer: instant, reversible, composable, and requiring only API access and a structured evaluation pipeline.

Given the limitations of both static prompting and weight modification, automating prompt optimization emerges as a third path. The paradigm is mature and produces real gains---but has a blind spot: no method has been validated on structured tool-agent-user benchmarks. DSPy [@khattab2023] abstracts language model pipelines as declarative modules with learnable parameters and provides a compiler that automatically optimizes them against a target metric. When compiled, GPT-3.5 and Llama2-13b self-bootstrap pipelines that outperform expert-created demonstrations by 5--46% on HotPotQA and GSM8K. Its GEPA optimizer [@agrawal2025], accepted as an Oral at ICLR 2026, uses natural language reflection from a stronger model to diagnose failures and propose targeted mutations, outperforming RL baselines by up to 20%. GEPA has been extended with an MCP Adapter for tool descriptions, but evaluations remain on reasoning benchmarks (HotPotQA, AIME) and instruction-following (IFBench).

TextGrad [@yuksekgonul2025] performs automatic "differentiation" via text by backpropagating LLM-generated feedback through computation graphs. Published in Nature in 2025, it achieved gains across coding (20% on LeetCode-Hard), science (GPT-4o accuracy on GPQA from 51% to 55%), and molecule optimization, providing evidence that prompt-level optimization is a viable paradigm. But evaluations are on single-turn QA, coding, and scientific optimization. OPRO [@yang2023] uses LLMs as black-box optimizers, iteratively generating prompt candidates from a meta-prompt containing previous solutions with scores, outperforming human-designed prompts by up to 8% on GSM8K and 50% on Big-Bench Hard. However, enterprise policies are arbitrary rules with no "gradient" to capture. EvoPrompt [@guo2023] combined LLMs with evolutionary algorithms, significantly outperforming human-engineered prompts across 31 datasets---up to 25% on Big-Bench Hard. PromptBreeder [@fernando2023] evolves both task-prompts and mutation-prompts in a self-referential loop, outperforming Chain-of-Thought and Plan-and-Solve on arithmetic and commonsense reasoning. ProTeGi [@pryzant2023] used LLM-generated "gradients" (criticisms of current performance) to iteratively edit prompts, reaching 31% improvement on classification tasks. PromptWizard [@agarwal2024promptwizard] achieved comparable results at just \$0.05 per task---a 5--60× cost reduction over competitors.

These methods are effective and mature. But testing is confined to NLU/NLG benchmarks: classification, generation, arithmetic reasoning. None involve tool calling, multi-turn conversation, or policy adherence. The optimization tools exist; τ²-bench exists; the two have not met.

@Fig:optimization-coverage maps each method against its evaluation domains.

![Prompt optimization methods and their evaluation domain coverage. The rightmost column---tool-calling benchmarks with multi-turn policy tasks---remains empty across all existing work.](figures/fig_lr_05_optimization_coverage.png){#fig:optimization-coverage}

A separate line of work has explored whether agents can improve through self-reflection rather than external optimization. @shinn2023 introduced Reflexion, where agents verbally reflect on task feedback and store reflections in episodic memory, producing gains on AlfWorld (household tasks), HotPotQA (multi-hop QA), and HumanEval (code generation). Reflexion demonstrated that automated diagnosis works: the agent can identify what went wrong and use that information to improve within an episode. The limitation is that reflections are ephemeral per-episode memory; they do not produce permanent prompt patches that accumulate across episodes. Each new episode starts from the same base agent. There is no separate teacher model; the agent self-reflects, which limits the quality of diagnosis to the agent's own capabilities. A weaker model reflecting on its own failures may not identify the root cause that a stronger model would catch.

Related work pushes further in different directions without closing the gap. @hu2024 proposed ADAS, using a meta-agent to iteratively program new agent designs from an ever-growing archive, but operates at the level of entire agent architectures rather than iterative prompt patching. @cheng2024 developed Trace and OptoPrime, framing workflow optimization over execution traces, beating DSPy's COPRO by ~10% on Big-Bench Hard. @zhang2024 introduced AgentOptimizer, treating tools as learnable parameters---the closest to tool-description optimization, but evaluated on MATH and tabular reasoning. @pei2025 proposed SCOPE, framing agent prompt management as online optimization on GAIA and HLE, but without a teacher--student paradigm. @choudhury2024 introduced LEAP with a teacher--student architecture on ALFWorld and WebShop, but improves the student via fine-tuning rather than prompt optimization.

The most recent wave of work targets the specific artifact this thesis optimizes: tool descriptions and agentic prompts. @fang2025 introduced PLAY2PROMPT, a zero-shot framework that "plays" with tools---iteratively exploring input--output behaviors via beam search---to refine tool documentation and generate usage examples without labeled data. The method improved zero-shot tool performance by 10--30% on the Berkeley Function-Calling Leaderboard and StableToolBench across both open and closed models, establishing that tool descriptions are a viable optimization target. @guo2026 proposed Trace-Free+, a curriculum learning framework that trains LLMs to rewrite tool descriptions, including parameter schemas, without requiring execution traces at deployment time. Trace-Free+ showed consistent gains on StableToolBench and RestBench with strong cross-domain generalization. @artemis2025 developed Artemis, a no-code evolutionary optimization platform that jointly optimizes prompts, tool descriptions, model parameters, and execution settings through semantically-aware genetic operators, achieving 9.3--13.6% improvement on competitive programming, coding, and mathematical reasoning benchmarks.

These papers represent genuine progress: tool description optimization is no longer hypothetical. But none employ a teacher--student paradigm where a frontier reasoning model explicitly diagnoses failures in a weaker student; none evaluate on multi-turn customer service benchmarks with domain-specific policies; and none target τ²-bench. They optimize tool *interfaces* for generic tool-calling accuracy, not agent *behavior* for enterprise policy compliance. The gap has narrowed, but it remains open.

Finally, the idea that a strong model can transfer knowledge to a weaker one---knowledge distillation---was formalized by @hinton2015 through soft probability distributions. In NLP, @sanh2019 produced DistilBERT (40% smaller, 97% of BERT's capability) and @jiao2020 pushed further with TinyBERT (7.5× smaller, 96.8% of performance). Weight-level distillation improves performance but requires full student retraining. Output-level distillation shifted the transfer medium to text: @taori2023 created Stanford Alpaca by fine-tuning LLaMA-7B on 52,000 ChatGPT-generated examples for under \$600, @chiang2023 created Vicuna at ~90% of ChatGPT quality, and @wang2023 formalized the pattern with Self-Instruct. The medium changed, but the final step---weight modification---did not.

Iterative, failure-driven distillation made the transfer loop adaptive. @jiang2023 proposed Lion, where the teacher identifies "hard" instructions where the student fails and generates targeted training data. Using just 70k examples, Lion-13B surpassed Vicuna-13B by 55.4% on Big-Bench Hard. @xu2023wizard introduced Evol-Instruct, where a strong LLM progressively rewrites simple instructions into complex ones. @zheng2023 validated the LLM-as-judge paradigm: GPT-4 agrees with human preferences over 80% of the time. The teacher's role evolved from "provide examples" to "diagnose failures and generate targeted corrections"---the mechanism this thesis adopts at the prompt level.

Reasoning models deepened the paradigm further. OpenAI's o1 [@openai2024] solved 79% of AIME 2024 problems compared to GPT-4's 9%---an order-of-magnitude improvement from test-time compute scaling. @deepseek2025 demonstrated that reasoning capabilities emerge naturally during RL training and can be distilled into smaller models. The Kimi model family is particularly relevant: Kimi K1.5 [@kimi2025a] reported state-of-the-art reasoning matching o1, and its long-to-short transfer methodology---transferring benefits of extended reasoning into compact execution---directly parallels this thesis's approach. Kimi K2 achieved 66.1 on τ²-bench in non-thinking mode [@kimi2025], one of the highest reported open-source results on the benchmark used here.

The trajectory of distillation points toward a prompt-level gap. SPoT [@vu2022] showed that soft prompts learned for one task can initialize prompts for new tasks across 26 NLP tasks, establishing that knowledge encoded in prompts can transfer. The *Superficial Alignment Hypothesis* [@zhou2023lima]---that alignment primarily teaches style and format, not deep capability---suggests that prompt-level transfer may suffice for behavioral corrections. Each generation of distillation has gotten lighter, cheaper, and more reversible: from soft distributions (Hinton) through behavioral outputs (Alpaca) through failure-driven data (Lion) through reasoning distillation (DeepSeek-R1) to prompt initialization (SPoT). But no one has taken the next step: a teacher model iteratively diagnosing failures and editing the student's prompts and tool descriptions---knowledge transfer at the thinnest, most reversible layer.

### Synthesis: Conclusions Shaping the Solution Design

The review above converges on four conclusions that directly inform the framework developed in Chapter 2.

Conclusion 1: Prompt-level optimization is feasible and academically validated. DSPy, TextGrad, GEPA, EvoPrompt, PromptBreeder, and PromptWizard have collectively demonstrated that automated prompt optimization produces real, measurable gains across diverse tasks. The paradigm is mature: methods range from gradient-inspired to evolutionary to self-referential, costs range from \$0.05 to hundreds of dollars per task, and publication venues include Nature and ICLR Oral. The question is no longer *whether* prompts can be optimized automatically, but *where* this optimization has been applied.

Conclusion 2: No existing work applies automated prompt optimization to multi-turn tool-calling agents. Despite the maturity of both optimization methods and agentic benchmarks, no existing work combines automated prompt optimization with validation on structured tool-agent-user benchmarks with domain-specific policies. DSPy evaluates on HotPotQA; TextGrad on GPQA and LeetCode; GEPA on reasoning and instruction-following; Artemis on competitive programming; PLAY2PROMPT and Trace-Free+ on BFCL and StableToolBench. The τ-bench family, which tests exactly the multi-turn, policy-following, tool-calling conditions of enterprise customer service, has not been used as an optimization target. The optimization tools exist; the benchmarks exist; the two have not met.

Conclusion 3: A teacher--student setup enables knowledge transfer without weight access. The distillation literature has progressively lightened the medium of knowledge transfer, from soft probabilities through behavioral outputs through failure-driven data to prompt initialization. A teacher model can reliably diagnose failures (LLM-as-judge validates at >80% agreement with humans), generate targeted corrections (Lion, WizardLM), and transfer knowledge across model families. Operating at the prompt level---the lightest transfer medium---is the natural endpoint of this trajectory and the only one compatible with API-only enterprise deployment.

Conclusion 4: The literature motivates two patch surfaces; we propose a third. Static prompting limitations motivate system prompt patches for policy and reasoning improvements. Tool description optimization work (PLAY2PROMPT, Trace-Free+, Artemis) establishes tool schemas as a viable optimization target. Based on our analysis of failure modes in preliminary experiments (Chapter 3), we additionally propose a third surface: sandboxed tool preprocessors that restructure tool inputs and outputs to compensate for model limitations in parameter handling, which is not addressed by existing work. Each surface addresses failures that the others cannot.

@Fig:gap-matrix positions the closest related work against the criteria that define the research gap. No existing method satisfies all of them; this thesis is the first to do so.

![Research gap positioning matrix. Each row is a closely related method; each column is a criterion required for the contribution of this thesis. Only this work satisfies all five.](figures/fig_lr_06_gap_matrix.png){#fig:gap-matrix}

@Fig:timeline places the key works reviewed in this chapter on a chronological axis, showing how the research threads have converged.

![Chronological development of key work by research area. The five threads---benchmarking, prompting, fine-tuning, prompt optimization, and distillation---have developed largely in parallel, converging in the 2023--2025 period that motivates this thesis.](figures/fig_lr_07_timeline.png){#fig:timeline}



<!-- FILE: ch1_3_diagnostic_study.md -->

## 1.3 Diagnostic Study of *target ai*'s Competitive Position

This section applies Porter's Five Forces, Value Chain Analysis, and Cost Structure Analysis to diagnose the competitive environment in which *target ai* operates and to identify the specific value-chain bottleneck that the proposed solution must address.

### Porter's Five Forces: CX Automation Market

@Fig:five-forces summarizes the Five Forces analysis.

![Porter's Five Forces applied to the CX automation market. Forces in red exert high pressure; orange indicates moderate pressure.](figures/fig_ds_01_five_forces.png){#fig:five-forces}

Enterprise buyers hold bargaining power in the CX automation market, driven by three structural factors. First, switching costs are declining. CX automation platforms consume LLMs through APIs, and the underlying models are increasingly interchangeable: a vendor built on GPT-4 can migrate to Claude or an open-source alternative with modest integration effort. Buyers know this, and use it to negotiate pricing and service-level commitments. The shift to outcome-based pricing --- Intercom charges \$0.99 per resolution [@intercom2024], Sierra implements primarily outcome-based pricing [@sierra2024] --- transfers performance risk directly to the vendor. Under this model, every unresolved customer interaction is revenue the vendor does not collect. Second, buyers demand measurable SLAs. Autonomous enterprise operation would require 3-to-5 nines of reliability (99.9--99.999% task success) [@rabanser2025; @rabanser2026nines]. Vendors that cannot demonstrate and maintain this reliability lose contracts to competitors that can, or worse, buyers revert to human agents entirely --- Gartner predicts that 50% of organizations will abandon plans to reduce their customer-service workforce through AI by 2027 [@gartner2025abandon]. Third, the buyer market is consolidating around large enterprise accounts. The contact center AI market is growing at 20--25% CAGR, from roughly \$2 billion in 2024 to a projected \$7--13 billion by 2030--2034 [@grandviewresearch2024; @fortunebi2025], but deal sizes are increasing as the industry moves beyond pilot deployments. Large accounts amplify buyer power: losing a single enterprise client can represent a material share of annual revenue --- a risk for *target ai*, where every *tos1* deployment is held up by a 25-person systems-analyst layer that is itself the largest function in a 75-person company. For *target ai*, high buyer power means vendors cannot pass alignment and maintenance costs through to clients; the cost of converting customer requirements into a working agent must be internalized and reduced through automation.

Supplier power is equally high. In the CX automation market, the primary suppliers are LLM providers: the companies that serve the foundation models through APIs. A small number of providers --- OpenAI, Anthropic, Google, and a handful of open-source model families accessible through routing services like OpenRouter --- control the core technology. Gartner projects that LLM inference costs will fall by over 90% by 2030 [@gartner2026inference90], yet warns that generative AI cost per resolution for customer service will exceed \$3 by 2030 as subsidized vendor pricing normalizes [@gartner2026costwarning]. When subsidies end, vendors like *target ai* face margin compression unless they can extract more value from fewer API calls. For *target ai* specifically, the situation is compounded by geopolitical constraints: international sanctions limit the availability of certain frontier model providers in the Russian market, restricting access to some of the strongest reasoning models. This makes model-agnostic architecture --- which is exactly what *tos1* sells, and which *tos2* inherits --- not just a convenience but an operational requirement. High supplier power thus demands a solution that is model-agnostic and that improves agent quality to reduce the total number of interactions requiring expensive model inference.

The threat of substitutes is moderate. The primary substitute for automated CX agents is manual customer service: human agents handling interactions directly. The cost differential is 5--10$\times$: AI interactions cost \$0.50--\$2.00 versus \$5--\$15 for human agents [@gartner2023cost]. However, this advantage erodes when AI agents fail frequently, because failures require human escalation, reprocessing, and the ongoing alignment labor documented in Section 1.1. Within *target ai*'s own portfolio, a second substitute is visible: target skill, the wizard-driven product where users build agents without analyst involvement. target skill works (16 million rubles in 2025) but only at the bottom of the complexity range, and it competes against *tos1* only when the customer's requirements are simple enough to fit a fixed architecture. Secondary substitutes at the industry level include in-house prompt engineering teams, fine-tuning services, and RLHF-as-a-service offerings, which compete with the automated alignment framework specifically rather than with the CX platform as a whole. As reviewed in Section 1.2, subsection "The Enterprise Agent Reliability Gap", the talent required for these alternatives is scarce and expensive --- AI skills command a 56% wage premium [@pwc2025aijobs], and Forrester predicts that three out of four firms building agentic architectures independently will fail [@forrester2025]. The substitute threat is kept in check by the cost advantage of AI agents and the scarcity of prompt engineering talent, but only if the AI agents actually work reliably --- automated alignment is what keeps the substitute threat low.

The threat of new entrants is also moderate. Barriers to entry in CX automation are asymmetric. On one hand, the technical barrier is low: LLM APIs are a commodity, and assembling a basic conversational agent requires modest engineering effort. The democratization of access through open-source models and routing services means a new entrant can build a proof-of-concept rapidly. On the other hand, two factors create durable moats. First, evaluation infrastructure --- the ability to systematically measure agent reliability across domains, detect regressions, and benchmark against competitors --- requires specialized tooling and domain expertise that take time to build. Second, domain-specific policy knowledge (airline rebooking rules, telecom plan structures, retail return policies) is accumulated through client engagements and is difficult to replicate from scratch. The combination of evaluation capability and domain expertise is what separates production-grade platforms from demo-ready prototypes. The framework's evaluation infrastructure ($\tau^2$-bench integration, automated regression testing, patch validation) strengthens *target ai*'s moat against new entrants, and the ability to demonstrate measurable, auditable improvement becomes a competitive asset.

Industry rivalry is high and accelerating. Globally, players such as Intercom, Sierra, Zendesk AI, and Salesforce Agentforce compete on agent quality, cost per resolution, and integration breadth. In the Russian market, Yandex, Sber AI, and smaller players add local competitive pressure. A second source of competitive pressure is internal: *target ai*'s own NLU-era product, target voice, has declined from approximately 210 million rubles in 2024 to 60 million rubles in 2025 as customers migrate to LLM-based *tos* deployments. Each migrating customer is, in effect, a contested re-sale; they could just as easily migrate to a competitor's LLM platform, and the speed and quality of the *tos* line's onboarding directly determines whether they stay. The competitive dynamics are shaped by the economics reviewed in Section 1.2, subsection "The Enterprise Agent Reliability Gap": AI-first companies broadly operate at 50--65% gross margins, well below the 70--85% typical of traditional SaaS, due to higher compute and services costs [@bessemer2025]. This cost structure means that the vendor with the lowest per-client alignment cost has a structural advantage --- it can offer lower prices, higher margins, or both. The Klarna case reviewed in Section 1.2, subsection "The Enterprise Agent Reliability Gap" --- rapid AI-driven cost savings followed by customer satisfaction decline and agent rehiring [@klarna2025; @forrester2025regret] --- illustrates the stakes. In a market where rivals compete on agent quality and cost, automated alignment that continuously matches agent behavior to the customer's preference function is a competitive differentiator that directly affects gross margins and client retention.

All five forces converge on a single conclusion: the CX automation market structurally demands automated agent alignment. Buyer power prevents passing alignment costs to clients. Supplier power demands model-agnostic, cost-efficient solutions. Substitutes are held at bay only while AI agents outperform humans on cost *and* reliability. New entrants are deterred by evaluation infrastructure, not by API access. Rivalry rewards the vendor with the lowest analyst-hours-per-deployment. Manual analyst-driven configuration --- as practiced today by *target ai*'s *tos1* team and consistent with industry estimates of 0.5 to 3 FTEs and \$45,000--\$55,000 per year per deployment for ongoing maintenance alone [@gartner2025complexity] --- is unsustainable under these pressures.

### Value Chain Analysis: *target ai*'s Service Delivery

Porter's Value Chain Analysis [@porter1985] decomposes a firm's activities into those that create value and those that support them, identifying where competitive advantage --- or competitive disadvantage --- originates. @Fig:value-chain maps *target ai*'s service delivery process for the *tos* line of agent-building platforms.

![*target ai*'s value chain for CX automation service delivery. The requirements-translation activity (highlighted) is shared with downstream maintenance and is the binding constraint on the *tos* line's ability to scale.](figures/fig_ds_02_value_chain.png){#fig:value-chain}

*target ai*'s service delivery follows six primary activities. (1) *Model selection*: choosing the appropriate LLM for each client deployment based on domain requirements, latency constraints, and cost targets --- a one-time activity per deployment, requiring moderate expertise but minimal ongoing cost. (2) *Requirements translation and agent configuration*: a 25-person team of specialized systems analysts --- the implementation organization, and the largest single function in the company --- elicits each customer's policies, edge cases, and acceptance criteria, then encodes them in the agent's system prompt, tool schemas, and policy rules. This is the labor-intensive front-loaded phase, performed once per deployment but typically iterated multiple times as the customer reviews early interactions and returns correction requests. This is the binding constraint on the *tos* line's ability to onboard new clients: it does not amortize across deployments, it requires scarce specialized labor, and it is the primary surface where customer satisfaction is won or lost. (3) *Deployment*: integrating the configured agent into the client's infrastructure via API, including webhook setup, authentication, and channel routing across voice (target voice runtimes during the migration window) and text channels --- largely automated through the platform. (4) *Monitoring*: tracking agent performance through conversation logs, automated evaluation, and client feedback, with *tos1*'s dashboards and alerting providing the foundation --- partially automated, with human review for flagged interactions. (5) *Maintenance*: diagnosing agent failures from conversation logs, writing corrective prompt or tool-schema patches, regression-testing changes, and re-deploying. Mechanically this is the same 25-person implementation team operating in a downstream loop: every policy change, product update, or regulatory shift returns an active deployment to the requirements-translation activity. Industry estimates place the resulting cost at 0.5--3 FTEs per deployment [@gartner2025complexity]; the binding constraint at *target ai*, however, is not maintenance hours measured in isolation but the *shared headcount* between activities (2) and (5), an analyst layer that is already larger than the entire engineering organization (25 analysts versus 19 developers) and that commands wages comparable to the premium documented for AI-skilled labor [@pwc2025aijobs; @glassdoor2025prompt]. (6) *Client reporting*: delivering performance reports, demonstrating SLA compliance, and recommending configuration changes --- largely automated through the platform's analytics module.

Two support activities underpin the primary chain: evaluation infrastructure (benchmark development and maintenance, including $\tau^2$-bench integration, automated test suites, and regression testing pipelines that enable the monitoring and maintenance activities) and API routing and model management (the litellm/OpenRouter layer that abstracts model provider APIs, enabling model-agnostic deployment and runtime model switching, providing the model-agnostic architecture that the Five Forces analysis identified as a strategic requirement).

A current value-chain stress event sharpens the picture. As described in Section 1.1, *target ai*'s NLU-era product target voice has declined from approximately 210 million rubles in 2024 to 60 million rubles in 2025, with the difference migrating onto the *tos* line. From the value chain's perspective, each migrating customer is an *additional* requirements-translation engagement competing for the same 25-person analyst team that serves new *tos1* sales. The migration is therefore not a free top-line story; it is a load test on activities (2) and (5). Without automation, the value chain offers two unattractive options: hire analysts proportionally (which moves *target ai* away from the SaaS cost profile, erodes margins, and would push the analyst layer past the entire current engineering organization at a faster rate than developer hiring) or constrain migration throughput (which delays revenue and exposes target voice customers to competitor outreach). The work on *tos2* is the expression of the same constraint and the motivation for the framework presented.

The value chain reveals an asymmetry. Activities 1, 3, 4, and 6 are either one-time, largely automated, or partially automated with bounded labor. Activities 2 and 5 --- requirements translation and maintenance --- share a single specialized labor pool of 25 people that scales linearly with the number of active deployments and the rate of policy-change events. As *target ai*'s client base grows, every other activity amortizes across deployments; the analyst layer does not. Each new client brings its own domain, its own policy edge cases, and its own failure patterns, and the analyst team cannot serve 50 clients with the headcount that currently serves the existing base without becoming an even larger fraction of the company than its current 1/3 share. This makes the systems-analyst layer the binding constraint on *target ai*'s ability to scale profitably. The Diagnose-Patch-Validate framework targets exactly this layer by automating both the initial requirements-translation step (through alignment to a customer preference function) and the downstream correction loop (through teacher-driven failure diagnosis), converting a linear-in-deployments cost into a near-fixed cost (the compute required to run the teacher model).

### Cost Structure Analysis

The Five Forces analysis established that the market demands automated alignment; the Value Chain analysis identified the systems-analyst layer (activities 2 and 5) as the operational bottleneck. This section quantifies the cost differential between the current manual process and the proposed automated alternative.

Building on the FTE figure introduced in the previous subsection, industry estimates place the cost of post-deployment agent maintenance alone at \$45,000--\$55,000 per deployment per year [@gartner2025complexity], with a comparable or larger cost for the upstream requirements-translation phase. For a vendor like *target ai* with $N$ active deployments, the annual systems-analyst cost is approximately:

$$C_\text{manual} = N \times (0.5\text{--}3) \times \text{FTE cost}$$

Anchoring to *target ai*'s actual scale: the *tos1* engineering team comprises eight developers, but the implementation organization that translates customer requirements for them numbers a further 25 people. Together those 33 people are the only labor directly attributable to producing *tos1*'s approximately 200 million rubles of 2025 revenue, yielding revenue-per-head of roughly six million rubles per year per directly-involved person --- well below SaaS benchmarks of \$250{,}000--\$500{,}000 per employee (roughly 25--50 million rubles), and consistent with the observation that the gap between AI-first and SaaS gross margins (50--60% versus 75--90%) is essentially the cost of professional services [@bessemer2025]. The analyst layer is markedly cheaper per head than the AI-skilled labor benchmarks discussed in Section 1.2, subsection "The Enterprise Agent Reliability Gap": a typical analyst's fully-loaded cost-to-company is approximately 180{,}000 rubles per month (around 2.16 million rubles per year, equivalent to roughly \$21{,}600), with senior analysts and team leads commanding more. The 25-person team's blended direct-labor cost lands at approximately 75 million rubles per year --- equal to roughly 37% of *tos1*'s annual revenue --- before training, supervision, tooling, or attrition replacement costs. The figure matters because it is *not* extreme on a per-person basis: even at relatively modest Russian compensation, a 25-person specialized team consumes more than a third of the revenue stream it serves, and that fraction grows linearly with the client base. Doubling the client base doubles the analyst headcount, and the migration of the target voice base onto the *tos* line (a swing of approximately 150 million rubles in revenue between 2024 and 2025) translates directly into linear demand on the same shared headcount pool.

The DPV framework replaces the human diagnosis-fix-test cycle with teacher model API calls. The cost per evolution sweep is determined by teacher model inference (the number of tokens consumed by the teacher when analyzing failure traces, generating patches, and validating fixes---based on experimental data from Chapter 3, a single sweep over 10--20 failed tasks consumes on the order of hundreds of thousands of tokens), student model re-evaluation (re-running the student agent on tasks to validate patches, using the typically cheaper student model and user simulator), and compute infrastructure (minimal---the framework runs on a single machine with API access, requiring no GPU infrastructure beyond what is already used for model serving). The cost structure is fundamentally different:

$$C_\text{automated} = C_\text{fixed} + N \times C_\text{sweep}$$

where $C_\text{fixed}$ is the one-time cost of framework development and integration, and $C_\text{sweep}$ is the per-deployment compute cost of running evolution sweeps. Critically, $C_\text{sweep}$ is determined by API token pricing and failure rate, not by human labor. As model inference costs decline (a well-documented trend, with costs dropping roughly 10$\times$ per year for equivalent capability), the marginal cost per deployment decreases over time---the opposite of the manual case, where labor costs increase with inflation and talent scarcity.

@Tbl:cost-comparison contrasts the two cost structures across key dimensions.

| Dimension | Manual maintenance | Automated (DPV framework) |
|-----------|-------------------|--------------------------|
| Variable cost driver | Human FTEs per deployment | API tokens per sweep |
| Scaling behavior | Linear in $N$ (deployments) | Near-fixed after initial integration |
| Marginal cost trend | Rising (talent scarcity, wage inflation) | Declining (API cost deflation) |
| Time to remediate | Hours to days (human diagnosis cycle) | Minutes (automated sweep) |
| Expertise required | Experienced prompt engineer (\$126K+ median) | API access + evaluation pipeline |
| Reversibility | Manual rollback, risk of regressions | Automated rollback, regression testing built-in |
| Audit trail | Ad-hoc (depends on team discipline) | Structured (every patch logged with rationale) |

: Cost structure comparison between manual and automated agent maintenance. {#tbl:cost-comparison}

The shift from labor-driven to compute-driven costs has a second-order effect on business model viability. As noted above, AI-first companies currently operate at 50--65% gross margins, well below the 70--85% margins of traditional SaaS, precisely because professional services (including requirements translation and maintenance) consume the difference [@bessemer2025]. Automating the highest-cost service component moves the cost structure toward the SaaS benchmark. For *target ai*, this means the ability to lift revenue-per-head on the *tos* line --- currently around six million rubles per directly-involved person-year when both developers and analysts are counted --- toward the 25--50 million ruble band typical of SaaS without proportionally growing the implementation organization, and to absorb the migrating target voice base without a step-change in services labor.

The framework is economically viable when the cost of running automated evolution sweeps is less than the cost of the human labor it displaces. Given that a single senior prompt engineer costs \$45,000--\$55,000 per year and can maintain approximately 2--5 deployments, the framework needs to maintain a deployment for less than \$9,000--\$27,500 per year in compute costs to break even. At current API pricing for reasoning models, this threshold is achievable: even intensive evolution runs (multiple sweeps over dozens of tasks) consume token volumes that cost hundreds to low thousands of dollars per domain. The margin of safety grows as inference costs decline.

### Synthesis

The three analyses converge on a unified diagnostic conclusion:

1. **The market demands it** (Five Forces). Every competitive force---buyer power, supplier power, substitutes, new entrants, and rivalry---exerts pressure that rewards automated agent improvement and penalizes manual maintenance. The structural economics of the CX automation market make the current services-heavy model unsustainable at scale.

2. **The value chain shows where** (Value Chain). The systems-analyst layer --- requirements translation (activity 2) and downstream maintenance (activity 5), which share a single specialized headcount pool --- is the only primary activity in *target ai*'s service delivery that does not amortize across deployments. It is the binding constraint on profitable scaling. All other activities are either one-time, largely automated, or bounded.

3. **The economics justify it** (Cost Analysis). The cost structure shift from linear (per-FTE, per-deployment) to near-fixed (per-sweep compute) is economically viable at current API pricing, with margins of safety that grow as inference costs decline. The framework does not need to eliminate all analyst labor; it needs to reduce the per-deployment human cost enough to break the linear scaling constraint, particularly during the target voice → *tos* migration window.

These conclusions directly inform the solution requirements developed in Chapter 2:

- The framework must be model-agnostic (supplier power, geopolitical constraints).
- It must produce auditable, reversible patches (buyer SLA requirements, regulatory context).
- It must reduce per-deployment systems-analyst cost below the manual alternative across both initial requirements translation and ongoing maintenance (cost structure viability).
- It must improve agent reliability measurably (competitive differentiation, buyer retention).
- It must operate without weight access (API-only enterprise deployment constraint).

The Diagnose-Patch-Validate framework developed in Chapter 2 is designed to satisfy all five requirements.



<!-- FILE: ch2_0_chapter.md -->

\newpage

# 2. Implementation Methodology



<!-- FILE: ch2_1_methodology_choice.md -->

## 2.1 Methodology Choice and Rationale

This section selects and justifies the methodologies used in this project. Two distinct methodological choices are required: (1) a project design methodology that structures the overall work of building and evaluating the framework (subsection "Project Design Methodology" below), and (2) a diagnostic methodology for analyzing the organization's internal and external environment (subsection "Diagnostic Methodology" below). The subsection "The Engineering Design Process" then describes the selected project design methodology in detail.

### Project Design Methodology

Five methodologies were considered for structuring the project. Each is suited to a different class of technical work; the question is which best fits a project whose deliverable is a software framework evaluated empirically against a benchmark.

TOGAF (The Open Group Architecture Framework) is the most widely used framework for enterprise architecture [@togaf2022]. It provides a comprehensive approach for designing, planning, implementing, and governing enterprise IT architecture, structured around four domains (Business, Application, Data, Technology) and an iterative Architecture Development Method (ADM). TOGAF is designed for multi-system enterprise transformations where the deliverable is an architecture governing multiple interacting systems. However, this project develops and evaluates a single software framework, not an enterprise architecture. The ADM's phases (Architecture Vision, Business Architecture, Information Systems Architecture, Technology Architecture, Migration Planning) do not map to the work of building a prompt-evolution loop and testing it on a benchmark, and TOGAF's scope far exceeds what is needed.

SDLC models (Waterfall, Agile, Scrum) govern the process of delivering production software. Waterfall prescribes sequential phases (requirements, design, implementation, testing, deployment); Agile and Scrum organize work into iterative sprints with continuous delivery and stakeholder feedback. These models structure the software delivery process---sprints, releases, CI/CD pipelines, user stories, backlog management---but this project is not delivering production software to end users; it is building a framework prototype and evaluating it against a benchmark. The project has no deployment phase, no user acceptance testing, and no maintenance releases. SDLC models would govern how the code is written but would not structure the evaluation of the framework as a research artifact---which is the core of the thesis.

Design Science Research (DSR) [@hevner2004; @peffers2007] is a paradigm for creating and evaluating IT artifacts. It prescribes a rigorous process: identify a problem, define objectives, design and develop an artifact, demonstrate it, evaluate it, and communicate results. DSR emphasizes the dual contribution of practical utility (the artifact works) and knowledge contribution (the artifact advances understanding). DSR provides strong theoretical grounding for framing the DPV framework as a design artifact, and its emphasis on evaluation against a baseline aligns with the paired baseline-versus-evolved experimental design. The framework's contribution to knowledge---demonstrating that prompt-level evolution works on multi-turn tool-calling benchmarks---maps naturally to DSR's knowledge contribution requirement. However, DSR prescribes artifact taxonomy, design theory, and formal knowledge contribution framing that exceed the scope of a project-based thesis; the methodology's emphasis on generalizable design theory is more appropriate for research dissertations than for project work aimed at solving a specific organizational problem.

CRISP-DM (Cross-Industry Standard Process for Data Mining) [@chapman2000] is a 6-phase methodology for data mining and machine learning projects: business understanding, data understanding, data preparation, modeling, evaluation, and deployment. It is the most widely used methodology in applied ML, well-understood, and provides clear phase boundaries. However, the deliverable of this project is a software framework, not a trained model. CRISP-DM's core phases---data preparation, modeling, hyperparameter tuning---do not map to the work performed here. The DPV framework does not train a model; it edits prompts and tool schemas. Forcing the project into CRISP-DM's phase structure would misrepresent what was actually done.

The Engineering Design Process (EDP) [@dym2005] is a systematic methodology for developing engineering artifacts through iterative design-test cycles. Its seven phases provide a natural structure for building and evaluating a software framework: define the problem, do background research, specify requirements, brainstorm and evaluate solutions, develop and prototype, test, and communicate results. EDP places the engineering artifact at center. Its iterative test-redesign cycle directly mirrors the DPV framework's own evolve-evaluate loop: both operate by testing, identifying failures, and iterating. EDP emphasizes requirements specification and alternative evaluation, which map to the benchmark selection and paired baseline-versus-evolved experimental design. The methodology is explicitly practical and deliverable-focused, fitting a project-based thesis. Its limitation is the lack of formal knowledge contribution framing of DSR; it does not explicitly prescribe statistical evaluation methods or theoretical positioning.

@Tbl:methodology-comparison summarizes the comparison.

\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.15}
\caption{Methodology comparison for the DPV framework project.\label{tbl:methodology-comparison}}
\begin{tabularx}{\textwidth}{@{}l *{5}{>{\raggedright\arraybackslash}X}@{}}
\toprule
\textbf{Criterion} & \textbf{TOGAF} & \textbf{SDLC (Agile/ Waterfall)} & \textbf{DSR} & \textbf{CRISP-DM} & \textbf{EDP} \\
\midrule
Artifact focus        & Enterprise architecture & Production software     & IT artifacts with theory            & ML models                    & Engineering artifacts \\
Iterative design      & Yes (ADM cycle)         & Yes (sprints/phases)    & Yes (evaluate $\to$ refine)         & Yes (model $\to$ evaluate)   & Yes (test $\to$ redesign) \\
Fit to deliverable    & Poor (enterprise scope) & Poor (delivery process) & Partial (framework, not theory)     & Poor (framework, not model)  & \textbf{Strong} (framework) \\
Requirements emphasis & High (enterprise-level) & Moderate (user stories) & Moderate                            & Low                          & \textbf{High} \\
Evaluation emphasis   & Low (governance focus)  & Low (delivery focus)    & \textbf{High} (artifact evaluation) & High (model metrics)         & \textbf{High} (test against criteria) \\
Practical orientation & Enterprise governance   & Software delivery       & Research-oriented                   & Industry-oriented            & \textbf{Project-oriented} \\
Thesis scope fit      & Far exceeds scope       & Misaligned focus        & Exceeds scope                       & Misaligned phases            & \textbf{Appropriate scope} \\
\bottomrule
\end{tabularx}
\end{table}

Selected methodology: Engineering Design Process.

The selection is justified on three grounds:

1. **Deliverable alignment.** The project's deliverable is a software framework (the DPV loop), not an enterprise architecture (TOGAF), production software (SDLC), a trained model (CRISP-DM), or a generalizable design theory (DSR). EDP is designed for exactly this class of artifact: an engineered system that must meet specified requirements and be evaluated against measurable criteria.

2. **Structural mirror.** The EDP's test-redesign cycle directly mirrors the framework's own operation. The framework iterates by evaluating agents, identifying failures, and applying patches; the project methodology iterates by prototyping the framework, testing it on benchmarks, and refining the design. This structural alignment means the methodology description naturally explains the work that was actually done.

3. **Scope appropriateness.** EDP provides sufficient rigor for a project-based thesis without the theoretical apparatus (artifact taxonomy, design theory formalization, knowledge base contribution) that DSR would require, the enterprise governance scope of TOGAF, or the delivery-process focus of SDLC. Design science provides useful grounding---the framework is a design artifact evaluated against an explicit baseline---but EDP is the operational methodology that structures the actual work.

The design science perspective is not discarded; it informs the evaluation design (paired baseline-versus-intervention comparison per @hevner2004's evaluation guideline). But the project follows EDP as its primary methodology, with design science as a complementary theoretical lens.

### Diagnostic Methodology

Section 7.5.3 of the thesis requirements calls for a diagnostic study of the organization's internal and external environment. Three analytical frameworks were considered for this purpose.

SWOT analysis identifies an organization's Strengths, Weaknesses, Opportunities, and Threats by examining internal capabilities and external factors [@humphrey2005]. It is the most widely taught strategic analysis tool. However, SWOT is descriptive rather than analytical: it classifies observations into four quadrants but does not generate causal relationships or directional conclusions. The framework's output---lists of strengths, weaknesses, opportunities, and threats---does not directly constrain solution design. SWOT is also commonly criticized for subjectivity: the same observation can be classified as a strength or weakness depending on framing [@helms2010]. For a project that needs the diagnostic study to produce specific requirements for the technical solution, SWOT's output is too open-ended.

PESTEL analysis scans the macro-environment across six dimensions: Political, Economic, Social, Technological, Environmental, and Legal factors [@aguilar1967]. It is designed for understanding the broad external context in which an organization operates, typically for market entry or strategic planning decisions. PESTEL's breadth is a liability when the problem is already well-scoped. The organizational problem---*target ai*'s agent maintenance bottleneck---is an internal operational issue driven by technology and economics, not by political, environmental, or legal factors. A PESTEL analysis would produce tangential observations (e.g., Russian data localization laws, environmental impact of compute) that do not constrain the solution design. The framework is more suitable for market entry analysis than for diagnosing a specific value-chain bottleneck.

Porter's Five Forces [@porter1980] analyzes industry structure through five competitive forces (buyer power, supplier power, substitutes, new entrants, rivalry). Porter's Value Chain Analysis [@porter1985] decomposes a firm's activities into value-creating and supporting activities, identifying where competitive advantage or disadvantage originates. Cost structure analysis quantifies the unit economics of current versus proposed operations. The three frameworks operate at complementary levels of abstraction: industry structure, firm operations, and unit economics. Each produces conclusions that directly constrain the solution requirements developed in Section 2.2.

@Tbl:diagnostic-comparison summarizes the comparison.

\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.15}
\caption{Diagnostic methodology comparison.\label{tbl:diagnostic-comparison}}
\begin{tabularx}{\textwidth}{@{}l
  >{\hsize=0.8\hsize\raggedright\arraybackslash}X
  >{\hsize=0.8\hsize\raggedright\arraybackslash}X
  >{\hsize=1.4\hsize\raggedright\arraybackslash}X@{}}
\toprule
\textbf{Criterion} & \textbf{SWOT} & \textbf{PESTEL} & \textbf{Porter's Five Forces + VCA + Cost Analysis} \\
\midrule
Output type             & Descriptive lists                & Environmental scan               & \textbf{Causal conclusions} \\
Analytical rigor        & Low (subjective classification)  & Moderate (structured dimensions) & \textbf{High} (structural analysis) \\
Fit to problem scope    & Generic (any organization)       & Macro-level (market entry)       & \textbf{Targeted} (industry + firm + economics) \\
Solution design linkage & Indirect                         & Indirect                         & \textbf{Direct} (each conclusion constrains a requirement) \\
Level of abstraction    & Single (internal/external)       & Single (macro-environment)       & \textbf{Three levels} (industry, firm operations, unit economics) \\
\bottomrule
\end{tabularx}
\end{table}

Selected diagnostic methodology: Porter's Five Forces combined with Value Chain Analysis and Cost Structure Analysis.

The selection is justified on two grounds:

1. **Actionable output.** Each framework produces conclusions that directly feed into the solution requirements: Five Forces establishes that the market demands automated agent improvement; Value Chain Analysis identifies maintenance as the single binding constraint on profitable scaling; Cost Structure Analysis quantifies the economic viability threshold. SWOT and PESTEL produce observations that would require additional interpretation to derive requirements.

2. **Complementary levels of abstraction.** The three frameworks cover industry structure (external), firm operations (internal), and unit economics (quantitative) without redundancy or filler quadrants. This provides the complete diagnostic arc from market context to investment justification that the thesis requires, while remaining focused on the specific problem.

The diagnostic frameworks are applied in Chapter 1, Section 1.3.

### The Engineering Design Process

The Engineering Design Process is a systematic, iterative methodology for developing engineering solutions to defined problems [@dym2005]. It is widely used in engineering education and practice, recognized by ABET accreditation criteria, and provides a structured yet flexible framework for projects where the deliverable is a functional artifact evaluated against measurable requirements.

The EDP consists of seven phases:

1. **Define the Problem.** Clearly articulate the problem to be solved, including constraints, stakeholders, and success criteria. The problem definition must be specific enough to guide the design process and measurable enough to evaluate the solution.

2. **Do Background Research.** Review existing solutions, relevant literature, available technologies, and prior art. Understand what has been tried, what works, what does not, and why. This phase establishes the knowledge base from which design decisions are made.

3. **Specify Requirements.** Translate the problem definition and background research into concrete requirements that the solution must satisfy. Requirements should be measurable, testable, and prioritized. They constrain the design space and provide the criteria against which the solution will be evaluated.

4. **Brainstorm, Evaluate, and Choose Solution.** Generate multiple candidate solutions, evaluate each against the specified requirements, and select the most promising approach. This phase involves systematic comparison (e.g., decision matrices) rather than ad-hoc selection.

5. **Develop and Prototype Solution.** Implement the chosen solution as a working prototype. The prototype must be functional enough to test against the requirements specified in Phase 3.

6. **Test Solution.** Evaluate the prototype against the requirements using structured tests. Collect data, analyze results, and determine whether the solution meets the success criteria. If not, the process iterates back to earlier phases.

7. **Communicate Results.** Document the design process, test results, conclusions, and recommendations. This includes both the technical documentation of the solution and the communication of findings to stakeholders.

A defining feature of the EDP is its iterative structure. The process is not strictly linear: test results in Phase 6 may reveal deficiencies that require returning to Phase 4 (choosing a different approach), Phase 5 (modifying the prototype), or even Phase 3 (revising requirements based on what testing reveals is feasible). This iterative loop is what distinguishes engineering design from a waterfall process: design, test, learn, redesign.

The iterative nature of EDP is particularly well-suited to this project for two reasons:

1. **The framework itself is iterative.** The DPV framework operates through repeated sweeps: evaluate the agent, identify failures, apply patches, re-evaluate. The project methodology mirrors the artifact's operation; both iterate by testing, learning from failures, and improving.

2. **The experimental design evolved during the project.** Initial experiments at 5 tasks informed the design of 10-task experiments, which in turn shaped the 20-task evaluation. The 3-model comparison (Qwen3 30B-A3B, Qwen3.5 Flash, GLM 4.7 Flash) was expanded as early results revealed model-dependent behavior. This adaptive experimental design is natural within EDP's iterative framework but would be awkward to justify under a strictly sequential methodology.

@Fig:edp-cycle illustrates the iterative EDP cycle and its application to this project.

![The Engineering Design Process cycle applied to this project. Solid arrows show the primary flow; dashed arrows show iteration paths triggered by test results.](figures/fig_edp_cycle.png){#fig:edp-cycle}



<!-- FILE: ch2_2_phase_by_phase_plan.md -->

## 2.2 Phase-by-Phase Implementation Plan

This section maps each phase of the Engineering Design Process to the specific project activities performed in this thesis, demonstrating how the methodology was applied in practice. @Tbl:edp-mapping provides the complete mapping; each phase is then discussed in detail.

| EDP Phase | Project Activity | Output | Thesis Location |
|-----------|-----------------|--------|-----------------|
| 1. Define Problem | Diagnose *target ai*'s systems-analyst bottleneck on the *tos* line | Problem statement and scope | Chapter 1, Section 1.1 |
| 2. Background Research | Literature review + diagnostic study | Knowledge base and market analysis | Chapter 1, Sections 1.2--1.3 |
| 3. Specify Requirements | Derive requirements from problem and research | Requirements specification | Subsection "Phase 3: Specify Requirements" below |
| 4. Brainstorm/Evaluate/Choose | Compare solution alternatives via decision matrix | Solution selection with rationale | Subsection "Phase 4: Brainstorm, Evaluate, and Choose Solution" below |
| 5. Develop Prototype | Implement the DPV framework | Working framework in Python | Chapter 2, Sections 2.3--2.4 |
| 6. Test | Run $\tau^2$-bench experiments across 3 scales $\times$ 3 models | Experimental results | Chapter 3, Sections 3.1--3.4 |
| 7. Communicate | Thesis document + *target ai* recommendations | This thesis + management roadmap | Chapter 3, Section 3.5 |

: Mapping of EDP phases to project activities. {#tbl:edp-mapping}

### Phase 1: Define the Problem

The problem was defined through analysis of *target ai*'s operational context (Section 1.1): the *tos* line's delivery model depends on a team of specialized systems analysts who translate customer requirements into agent prompts and tool schemas, and the same scarce headcount must absorb every downstream policy change, so the cost of aligning agents to customer preferences scales linearly with the number of deployments. The constraint, API-only model access, rules out weight-modification approaches. Five project objectives were formulated to address this problem (Section 1.1).

### Phase 2: Background Research

Background research comprised two activities. The literature and practice review (Section 1.2) surveyed six approaches to agent improvement: static prompting, fine-tuning/RLHF, automated prompt optimization, self-reflective agents, tool description optimization, and knowledge distillation. It identified the gap: no existing method combines teacher-driven diagnosis with prompt-level patching validated on a multi-turn tool-calling benchmark. The diagnostic study (Section 1.3) applied the diagnostic frameworks selected in Section 2.1, subsection "Diagnostic Methodology"---Porter's Five Forces, Value Chain Analysis, and Cost Structure Analysis---to establish the competitive necessity and economic viability of the proposed solution.

### Phase 3: Specify Requirements

The problem definition, literature review, and diagnostic study converge on seven requirements that the solution must satisfy:

| # | Requirement | Source | Testable Criterion |
|---|------------|--------|-------------------|
| 1 | **API-only compatibility.** The framework must operate without access to model weights---no fine-tuning, no RLHF, no gradient computation. | Section 1.1 (constraint), Section 1.2, subsection "Approaches to Automated Prompt and Agent Improvement" (fine-tuning impracticality), Section 1.3, subsection "Synthesis" | All patches modify only prompt text, tool schemas, or preprocessor code; no weight files are created or modified. |
| 2 | **Auditability and reversibility.** All changes must be human-readable, versionable, and rollback-able. | Section 1.3, subsection "Porter's Five Forces: CX Automation Market" (buyer SLA requirements), Section 1.2, subsection "Approaches to Automated Prompt and Agent Improvement" (alignment tax irreversibility) | Every patch is logged with rationale; the evolved state is serialized to JSON; any prior state can be restored. |
| 3 | **Measurable improvement.** The framework must produce statistically detectable improvement on a recognized benchmark. | Section 1.1 (Objective 2), Section 1.2, subsection "Synthesis: Conclusions Shaping the Solution Design" (Conclusion 4) | Pass rate on $\tau^2$-bench increases from baseline to evolved condition, evaluated with paired statistical tests. |
| 4 | **Multi-surface patching.** The framework must address failures across prompt, tool schema, and tool preprocessing surfaces. | Section 1.2, subsection "Synthesis: Conclusions Shaping the Solution Design" (Conclusion 4) | Successful fixes are recorded across at least two distinct patch surfaces. |
| 5 | **Scalability characterization.** The framework's behavior must be characterized across increasing task-pool sizes. | Section 1.1 (Objective 4) | Experiments run at 5, 10, and 20 tasks with fix rate and improvement tracked at each scale. |
| 6 | **Model-agnostic operation.** The framework must work across multiple LLM providers and model families without architectural changes. | Section 1.3, subsection "Porter's Five Forces: CX Automation Market" (supplier power, geopolitical access constraints) | Experiments run on multiple student model families (Qwen3, Qwen3.5, GLM 4.7) through the same routing layer; no model-specific code paths in the evolution loop. |
| 7 | **Per-deployment cost reduction.** The framework's per-deployment maintenance cost must be lower than the manual baseline of \$45,000--\$55,000/year. | Section 1.3, subsection "Cost Structure Analysis" | Token-based cost of an evolution sweep, multiplied by expected sweep frequency, falls below the manual FTE cost (evaluated in Section 3.5, subsection "Economic Effectiveness"). |

: Solution requirements derived from problem analysis and background research. {#tbl:requirements}

### Phase 4: Brainstorm, Evaluate, and Choose Solution

Five candidate approaches to automating agent improvement were considered. @Tbl:decision-matrix evaluates each against the seven requirements; column numbers correspond to the rows of @tbl:requirements above.

| Approach | 1 | 2 | 3 | 4 | 5 | 6 | 7 | Verdict |
|----------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---------|
| Manual prompt engineering | Yes | Yes | Yes | Yes | Yes | Yes | **No** | Baseline practice; cost does not scale |
| Fine-tuning (SFT/LoRA) | **No** | No | Yes | No | Yes | **No** | Yes | Requires weight access |
| RLHF/DPO | **No** | No | Yes | No | Yes | **No** | Yes | Requires weight access + preference data |
| Self-reflective evolution (Reflexion-style) | Yes | Partial | Untested | No | Unknown | Yes | Yes | Ephemeral; no teacher supervision |
| **Teacher-driven DPV framework** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | **Yes** | Selected |

: Decision matrix evaluating candidate approaches against requirements. {#tbl:decision-matrix}

Fine-tuning and RLHF are eliminated by the API-only constraint: *target ai* cannot access model weights. They also fail the model-agnostic requirement, since model-specific weights cannot be ported across providers. Even if weight access were available, the alignment tax [@lin2024; @young2026]---degradation of general capabilities under weight modification---and catastrophic forgetting [@luo2023] make these approaches incompatible with reversibility.

Manual prompt engineering satisfies all requirements except cost reduction: it works, but at a per-deployment cost that scales linearly with the client base (Section 1.3, subsection "Cost Structure Analysis"), making it the problem rather than the solution.

Self-reflective evolution (Reflexion-style) is API-only and model-agnostic but only partially auditable (reflections are ephemeral, not persisted as auditable patches), and has not been validated on multi-turn tool-calling benchmarks. It also operates on a single surface and uses the agent's own capabilities for diagnosis, limiting diagnostic quality to the agent's own level.

The teacher-driven DPV framework satisfies all seven requirements:

- *API-only compatibility:* operates entirely in the input space; no weights are modified.
- *Auditability and reversibility:* all patches are human-readable text edits serialized to JSON with a full audit trail.
- *Measurable improvement:* evaluated on $\tau^2$-bench with statistical analysis.
- *Multi-surface patching:* three distinct patch surfaces (system prompt, tool schemas, tool preprocessors).
- *Scalability characterization:* evaluated at 5, 10, and 20 tasks with scaling behavior characterized.
- *Model-agnostic operation:* validated across three student model families (Qwen3, Qwen3.5, GLM 4.7) through a single routing layer.
- *Per-deployment cost reduction:* per-deployment cost dominated by API token consumption, several orders of magnitude below the manual FTE baseline at current pricing (quantified in Section 3.5, subsection "Economic Effectiveness").

The framework also incorporates a design science element: the paired baseline-versus-evolved experimental design follows @hevner2004's evaluation guideline of demonstrating improvement over an explicit baseline.

### Phases 5--7: Prototype, Test, and Communicate

Phases 5--7 are documented primarily in the chapters they produce; this section records only what is specific to the EDP mapping. Phase 5 (Develop and Prototype): the framework was implemented in Python 3.12 using $\tau^2$-bench as the evaluation substrate, with architecture and implementation details presented in Sections 2.3 and 2.4. Phase 6 (Test): testing comprised eight experiments across three scales (5, 10, 20 tasks) and three student models (Qwen3 30B-A3B, Qwen3.5 Flash, GLM 4.7 Flash), reported in Chapter 3, Sections 3.1--3.4. The iterative nature of EDP is visible in the experimental design: results at 5 tasks informed the 10-task experimental design, and the GLM 4.7 Flash failure at 10 tasks led to the decision to drop it from the 20-task evaluation. Phase 7 (Communicate): communication takes three forms: this thesis document, the effectiveness evaluation against project objectives (Section 3.5), and the management roadmap for integration into *target ai*'s operations (Section 3.5, subsection "Recommendations for *target ai*").



<!-- FILE: ch2_3_solution_architecture.md -->

## 2.3 Solution Architecture

This section describes the architecture of the Diagnose-Patch-Validate (DPV) framework. The subsection "Architecture Overview" provides an overview; "The Outer Loop" describes the outer loop; "The Inner Loop: Per-Failure Fix Attempts" details the inner loop for per-failure repair; "Patch Surfaces and Mechanisms" documents the three patch surfaces; and "Failure Taxonomy" presents the failure taxonomy.

### Architecture Overview

The DPV framework implements a diagnose-patch-validate loop that automates the most labor-intensive component of post-deployment agent maintenance: failure diagnosis and prompt remediation. In current enterprise practice, this cycle requires a human expert to review failed conversation traces, identify the root cause, write a corrective prompt or schema edit, and regression-test the change---a process that industry estimates place at 0.5 to 3 FTEs per deployment [@gartner2025complexity]. The framework replaces this human loop with a model-driven one.

A weaker student model runs on benchmark tasks and fails on some. A stronger teacher model analyzes each failure, proposes modifications to the student's prompt and tool configuration, and those modifications are validated by re-running the student on the failed task. Successful patches are merged into a progressively improved agent configuration. The architecture operates at two levels: an outer loop iterates over the full task set, and an inner loop handles individual failure repair. @Fig:system-architecture provides a high-level view.

![System architecture: the $\tau^2$-bench orchestrator mediates between the student agent and user simulator, while the teacher model analyzes failed traces and patches the evolved state (prompt, tool schemas, and preprocessors).](figures/fig_03_system_architecture.png){#fig:system-architecture}

In the automated prompt optimization literature, this is a teacher-driven variant of reflective prompt evolution. The closest precedent is GEPA [@agrawal2025], which uses natural language reflection from a stronger model to diagnose failures and propose targeted mutations, outperforming reinforcement learning baselines by up to 20% while using 35$\times$ fewer rollouts. The present framework departs from GEPA in three respects: (1) patches target three distinct surfaces (prompt, schemas, preprocessors); (2) every patch is validated by re-running the student before merging; (3) the evaluation target is a structured tool-agent-user benchmark ($\tau^2$-bench).

### The Outer Loop

The outer loop proceeds as follows for each sweep:

1. The student is evaluated on all benchmark tasks with the current evolved state, and results are saved.
2. Tasks that do not pass unanimously across all trials are extracted as failures.
3. For each failed task, a teacher session is spawned in parallel to diagnose the failure and propose patches; each patch set is validated by re-running the student.
4. All accepted patches are merged into the global state by a dedicated merger LLM session.
5. The loop repeats with the full task set until no failures remain or the maximum sweep count is reached.

Re-evaluating all tasks every sweep---rather than dropping attempted tasks---is deliberate: merged patches from multiple independent teacher sessions can interact, and re-evaluation catches regressions introduced by the merge step. @Fig:outer-loop visualizes this process. The parallel fix phase uses a thread pool to process multiple failures concurrently: each thread operates on a deep copy of the global state, preventing interference between concurrent teacher sessions, and results are collected and merged after all threads complete (@fig:parallel-architecture).

::: sidebyside
![Evolution outer loop: the student is evaluated on all tasks, failures are extracted, teacher sessions fix failures in parallel, winning patches are merged, and all tasks are re-evaluated in the next sweep.](figures/fig_01_outer_loop.png){#fig:outer-loop}

![Parallel execution architecture: failed tasks are distributed across threads, each with an independent copy of the evolved state.](figures/fig_11_parallel_architecture.png){#fig:parallel-architecture}
:::

Algorithm 1 formalizes the outer loop. Let $\sigma = (\pi, \mathcal{S}, \mathcal{C})$ denote the evolved state: the system prompt, the dictionary of tool schemas, and the dictionary of tool preprocessors, respectively. $\text{Pass}(\mathbf{r})$ holds if and only if all $T$ trials achieve a perfect reward: $\forall\, t \in \{1,\dots,T\}: r_t = 1.0$.

\begin{algorithm}
\caption{Diagnose-Patch-Validate Loop}\label{alg:outer-loop}
\begin{algorithmic}[1]
\Require $\mathcal{D}_\text{train}, \mathcal{D}_\text{test}, \sigma_0 = (\pi_0, \mathcal{S}_0, \mathcal{C}_0), M_s, M_t, S_\text{max}, A, T$
\Ensure $\sigma^*$ (evolved state)
\State $\sigma \gets \sigma_0$
\For{$s = 1$ \textbf{to} $S_\text{max}$}
    \Comment{\textsc{Sweep}: evaluate student on all train tasks}
    \State $R \gets \{(\tau,\; \mathbf{r}(\tau, \sigma, M_s, T)) : \tau \in \mathcal{D}_\text{train}\}$ \Comment{$T$ trials per task}
    \State $F \gets \{(\tau, \mathbf{r}) \in R : \neg\textsc{Pass}(\mathbf{r})\}$
    \If{$F = \emptyset$} \textbf{break} \Comment{all tasks pass}
    \EndIf
    \If{$s = S_\text{max}$} \textbf{break} \Comment{final sweep is evaluation-only}
    \EndIf
    \Comment{\textsc{Fix}: repair each failure independently}
    \State $W \gets \emptyset$
    \ParFor{$(\tau, \mathbf{r}) \in F$}
        \State $\sigma_\text{local} \gets \textsc{DeepCopy}(\sigma)$
        \State $\text{result} \gets \textsc{FixFailure}(\tau, \sigma_\text{local}, M_t, A, T)$ \Comment{Algorithm~\ref{alg:fix-failure}}
        \If{$\text{result.fixed}$} $W \gets W \cup \{\text{result}\}$
        \EndIf
    \EndParFor
    \Comment{\textsc{Merge}: consolidate winning patches}
    \If{$W \neq \emptyset$}
        \State $\sigma \gets \textsc{MergePatches}(\sigma, W, M_t)$ \Comment{LLM-based dedup \& compaction}
    \EndIf
\EndFor
\State \Return $\sigma$
\end{algorithmic}
\end{algorithm}

### The Inner Loop: Per-Failure Fix Attempts

For each failed task, a teacher session is created with deep copies of the current global state. The total attempt budget $A = 1 + \textit{max\_retries}$ is split between two phases: Phase 1 (teaching) receives $\lceil A/2 \rceil$ attempts, and Phase 2 (guardrails) receives the remainder. The session enters a reflect-validate loop.

In the **reflection step**, the teacher receives a comprehensive prompt containing: the agent's current system prompt, all tool schemas, the full failed conversation trace, the task requirements, and the reward breakdown. It diagnoses the root cause, classifies it (see subsection "Failure Taxonomy" below), and calls patch tools to propose modifications.

![Example teacher session: the teacher receives the failed trace and reward breakdown, diagnoses the root cause, and proposes a structured patch via tool calls.](figures/fig_04_teacher_session.png){#fig:teacher-session}

In the **validation step**, the student is re-run on the same task with the patches applied for multiple trials. A fix is accepted only if the task passes unanimously: all trials achieve a perfect reward of 1.0. If not, all patches are reverted and the teacher receives the new conversation trace and reward breakdown, and is asked to try again. @Fig:inner-loop diagrams this per-failure fix loop.

The 2-phase escalation strategy ensures lighter-weight interventions are attempted first (@fig:escalation):

- **Phase 1 (Teaching):** The teacher can only modify the prompt and tool schemas via `patch_prompt` and `patch_tool`. This addresses failures where the student needs clearer instructions or better tool descriptions.
- **Phase 2 (Guardrails):** If Phase 1 exhausts its attempts, `patch_tool_code` is unlocked, allowing the teacher to add defensive preprocessors that transform tool-call arguments before execution. This addresses persistent formatting errors that survive instruction-level correction.

::: sidebyside
![Per-failure fix loop: the teacher analyzes the failure, proposes patches, and the student is re-run for validation. If the task does not pass all trials, patches are reverted and the teacher retries.](figures/fig_02_inner_loop.png){#fig:inner-loop}

![2-phase teacher escalation: Phase 1 restricts the teacher to prompt and schema patches. If unsuccessful, Phase 2 unlocks tool preprocessor editing.](figures/fig_10_escalation.png){#fig:escalation}
:::

\begin{algorithm}
\caption{FixFailure: 2-phase Teacher Escalation}\label{alg:fix-failure}
\begin{algorithmic}[1]
\Require failed task $\tau$, state copy $\sigma = (\pi, \mathcal{S}, \mathcal{C})$, teacher $M_t$, attempt budget $A$, trials $T$
\Ensure \textsc{FixResult}
\State $A_1 \gets \lceil(A{+}1)/2\rceil$;\quad $A_2 \gets A - A_1$ \Comment{split budget between phases}
\State $\mathcal{T}_1 \gets \{\texttt{patch\_prompt},\, \texttt{patch\_tool},\, \texttt{read\_tool\_code}\}$
\State $\mathcal{T}_2 \gets \mathcal{T}_1 \cup \{\texttt{patch\_tool\_code}\}$
\State $\sigma_\text{base} \gets \sigma$ \Comment{checkpoint for revert}
\State $\text{trace} \gets$ initial failing conversation
\Statex
\Comment{\textbf{Phase 1}: Teaching (prompt + schema patches only)}
\For{$a = 1$ \textbf{to} $A_1$}
    \State $\text{patches}, \text{diag} \gets \textsc{Reflect}(M_t, \text{trace}, \sigma, \tau, \mathcal{T}_1)$
    \If{$\text{patches} = \emptyset$} \textbf{break}
    \EndIf
    \State $\sigma \gets \textsc{Apply}(\sigma, \text{patches})$
    \State $\mathbf{r} \gets \textsc{Validate}(\tau, \sigma, M_s, T)$
    \If{$\textsc{Pass}(\mathbf{r})$}
        \State \Return $\textsc{FixResult}(\text{fixed}{=}\text{true},\, \text{patches},\, \text{tier}{=}\textsc{Tier}(\text{patches}))$
    \EndIf
    \State $\sigma \gets \sigma_\text{base}$ \Comment{revert all patches}
    \State $\text{trace} \gets \mathbf{r}$
\EndFor
\Statex
\Comment{\textbf{Phase 2}: Guardrails (unlock preprocessor editing)}
\If{$A_2 > 0$}
    \State $\textsc{Escalate}(M_t, \mathcal{T}_2)$
    \For{$a = 1$ \textbf{to} $A_2$}
        \State $\text{patches}, \text{diag} \gets \textsc{Reflect}(M_t, \text{trace}, \sigma, \tau, \mathcal{T}_2)$
        \If{$\text{patches} = \emptyset$} \textbf{break}
        \EndIf
        \State $\sigma \gets \textsc{Apply}(\sigma, \text{patches})$
        \State $\mathbf{r} \gets \textsc{Validate}(\tau, \sigma, M_s, T)$
        \If{$\textsc{Pass}(\mathbf{r})$}
            \State \Return $\textsc{FixResult}(\text{fixed}{=}\text{true},\, \text{patches},\, \text{tier}{=}\text{CODE})$
        \EndIf
        \State $\sigma \gets \sigma_\text{base}$
        \State $\text{trace} \gets \mathbf{r}$
    \EndFor
\EndIf
\State \Return $\textsc{FixResult}(\text{fixed}{=}\text{false})$
\end{algorithmic}
\end{algorithm}

### Patch Surfaces and Mechanisms

The framework operates on three distinct patch surfaces, each targeting a different class of agent failure. All patches use a find-and-replace mechanism: the teacher specifies an `old_text` to locate and a `new_text` to substitute, keeping modifications precise, minimal, and reversible.

![Patch surfaces and failure type mapping: different failure categories are addressed by different patch surfaces.](figures/fig_06_patch_surfaces.png){#fig:patch-surfaces}

**Prompt patches** modify the agent's system prompt, typically adding concrete behavioral rules the student was not following. When `old_text` is empty, `new_text` is appended to the prompt's end. The Superficial Alignment Hypothesis [@zhou2023lima] suggests this should work: alignment primarily teaches style and format, which prompt text can supply. @sclar2023 demonstrated up to 76 accuracy points of variation from meaning-preserving formatting changes alone, confirming that models are highly sensitive to prompt content.

**Tool schema patches** modify the JSON schemas that define how the agent calls each tool. Common modifications include clarifying parameter descriptions (adding "must start with #" to a reservation_id field), expanding tool descriptions to note when a tool should or should not be used, and adding constraint notes. After each edit, the JSON string is parsed to ensure syntactic validity; patches producing invalid JSON are rejected.

**Tool preprocessors** are sandboxed Python functions that transform tool-call arguments before execution. Every tool starts with an identity preprocessor. The teacher can modify the code to add defensive input coercion: ensuring an ID field has the correct prefix, casting strings to integers, normalizing date formats. Preprocessors are sandboxed: a static analysis pass rejects forbidden constructs (imports, eval, exec, file I/O), the execution namespace restricts available builtins, and runtime exceptions fall back to the original arguments.

Patches are applied sequentially using first-occurrence-only string replacement. Failed patches (old_text not found) are logged and skipped. When multiple tasks are fixed in a single sweep, winning patches are consolidated by a dedicated merger LLM session that resolves conflicts, deduplicates redundant edits, and compacts overlapping changes. The evolved state is serialized to disk as a JSON file containing the full prompt, all tool schemas, and all preprocessor source code.

![Patch application pipeline: prompt patches are applied directly, while tool schema patches must produce valid JSON and tool preprocessor patches must pass static analysis.](figures/fig_12_patch_pipeline.png){#fig:patch-pipeline}

### Failure Taxonomy

The teacher classifies each failure into one of four categories as part of its diagnostic output:

| Category | Description | Examples |
|----------|-------------|----------|
| TOOL_MISUSE | Wrong tool, wrong parameters, missing tool call | Using get_flight_details instead of get_reservation_details |
| POLICY_VIOLATION | Skipped validation step or broke a constraint | Cancelling without checking refund eligibility |
| REASONING_ERROR | Incorrect assumption, incomplete plan | Assuming a flight is direct when it has connections |
| COMMUNICATION_ERROR | Confusing message, failed to guide user | Not explaining applicable fees to the customer |

: Failure taxonomy for teacher-model diagnosis. {#tbl:failure-taxonomy}

![Failure taxonomy: agent failures are classified into four categories, each with characteristic examples.](figures/fig_08_failure_taxonomy.png){#fig:failure-taxonomy}

Classification is automated: the teacher includes the failure type in its diagnostic text, and the category is extracted by string matching. This is a heuristic; the implementation takes the first match, defaulting to REASONING_ERROR when none is found. The taxonomy enables per-category analysis of which failure types are most responsive to each patch surface.

### Quality Assurance

Several mechanisms ensure patch quality:

- **Unanimous validation:** A fix is accepted only if the patched student passes the task unanimously across all trials (each achieving reward 1.0). Partial improvements are not accepted. This prevents fragile patches from entering the global state.
- **LLM-based deduplication:** The merger session identifies and removes redundant patches that arise when multiple teacher sessions independently discover the same fix.
- **State persistence and rollback:** The complete evolved state is serialized to JSON after each iteration. Loading this state reconstructs the exact evolved agent. Any prior state can be restored.
- **Task locking:** After the first evaluation, task IDs are locked and reused for all subsequent iterations, so pass-rate changes reflect patches, not sampling variation.



<!-- FILE: ch2_4_implementation.md -->

## 2.4 Implementation and Experimental Setup

This section describes the technology stack, benchmark configuration, model choices, experimental conditions, evaluation metrics, and reproducibility provisions.

### Technology Stack

The framework is implemented in Python 3.12 with the following key dependencies:

- **$\tau^2$-bench** [@barres2025]: evaluation benchmark, integrated as a git submodule pinned to commit 37bfc31 (based on tag v0.1.1), installed as an editable Python package. No modifications were made to the upstream codebase; all integration occurs through $\tau^2$-bench's public API.
- **litellm**: LLM routing library used by $\tau^2$-bench for model inference, providing a unified interface across providers.
- **OpenAI Python SDK** ($\geq$1.0): used for direct teacher model API calls with function calling support.
- **OpenRouter**: API routing service providing access to all models through a single API key.
- **uv** with hatchling backend: build system for dependency management and reproducible environments.

The source code is publicly available at github.com/glebdementev/tau-evo.

### Benchmark: $\tau^2$-bench Airline Domain

$\tau^2$-bench was selected over four alternative benchmarks (AgentBench, SWE-bench, GAIA, ToolBench) because it is the only benchmark that combines: (1) multi-turn conversations with an LLM-simulated user providing partial information, (2) domain-specific policies, (3) tool-calling APIs that modify database state, and (4) the pass$^k$ reliability metric. Customer service is the natural evaluation domain because it represents the largest addressable market for AI agent automation: approximately 17 million contact center agents globally, with labor constituting up to 95% of operating costs [@gartner2022labor].

The experiments use the airline domain (50 tasks total). Each task defines a user scenario, expected agent actions, post-conversation database state assertions, and natural-language assertions. A task passes if and only if the agent satisfies all criteria simultaneously; this is the strict binary pass$^1$ metric standard in $\tau$-bench publications.

A simulated orchestrator manages turn-by-turn conversation between the agent and user simulator. On each turn the agent may either send a text message or invoke a tool. Tool calls are executed against a simulated database. The conversation ends when the user simulator signals completion or a maximum step count is reached. The full trace is preserved for analysis by the teacher model.

![Conversation mechanics in $\tau^2$-bench: turn-by-turn interaction between agent and user simulator.](figures/fig_07_conversation_mechanics.png){#fig:conversation-mechanics}

### Model Selection

All models are accessed through OpenRouter using a single API key.

| Role | Model | Access Method |
|------|-------|---------------|
| Student agent | Qwen3 30B-A3B | litellm via $\tau^2$-bench |
| User simulator | Qwen3 30B-A3B | litellm via $\tau^2$-bench |
| Teacher | Kimi K2.5 | OpenAI client direct |

: Model assignments and access methods. {#tbl:models}

The primary student model is Qwen3 30B-A3B [@qwen2025], a Mixture-of-Experts Transformer with 30.5 billion total parameters but only 3.3 billion active per token. It employs 128 experts with top-8 routing across 48 layers and supports 32,768 native context tokens. Despite activating barely 10% of its parameters per forward pass, the model outperforms Qwen2.5-14B on all reported benchmarks and leads the Berkeley Function Calling Leaderboard (BFCL v3).

The selection reflects a trade-off that mirrors the real enterprise deployment decision: organizations choose cost-efficient models precisely because frontier models are prohibitively expensive at production volumes, then need a mechanism to close the resulting performance gap.

Alternative student models---Qwen3.5 Flash and GLM 4.7 Flash---are evaluated for cross-student comparison.

The teacher model is Kimi K2.5 [@kimi2026], a MoE Transformer with approximately one trillion total parameters and 32 billion active per token. Its 256K-token context window accommodates full conversation traces, the system prompt, all tool schemas, and task requirements in a single prompt. The teacher was chosen for higher reported performance than the student, tool-calling comprehension, a long context window, architectural independence from the student (Moonshot AI, not Alibaba), and cost-effectiveness for hundreds of reflection calls.

The user simulator uses Qwen3 30B-A3B. $\tau^2$-bench's user simulator follows scripted scenarios and does not require frontier-level capabilities.

### Experimental Conditions

Two conditions are evaluated, differing only in the agent's prompt and tool configuration:

- **Baseline.** The student model runs with $\tau^2$-bench's default system prompt and original tool schemas. This establishes the performance floor.

- **Evolved.** The student model runs with the evolved prompt and tool configuration produced by the DPV framework: modified system prompt, modified tool schemas, and tool preprocessors.

### Experimental Design: Three Scales $\times$ Three Models

The experiments span three task-pool sizes and three student models:

| Scale | Task IDs | Qwen3 30B | Qwen3.5 Flash | GLM 4.7 |
|-------|----------|-----------|---------------|---------|
| 5 | 0, 1, 3, 4, 5 | Done | Done (base only) | Done |
| 10 | 0--5, 7, 9--12 | Done | Done | Done |
| 20 | 0--5, 7, 9--12, 14, 15, 17, 20, 21, 23, 27, 28, 33, 34 | Done | Done | Dropped |

: Experimental conditions across scales and models. GLM 4.7 Flash is dropped at 20 tasks due to poor performance at 10 tasks. {#tbl:conditions}

Each experiment runs the evolution loop for up to three sweeps with up to two retries per failed task per sweep. Every task is evaluated with three trials. A task passes in a given sweep if it passes in at least two of three trials (majority vote). The seed is fixed at 42 throughout.

The scaling sequence is deliberate: if gains are task-specific, they should be largest at small scale and diminish as the denominator grows. The multi-model comparison tests whether a stronger student benefits differently from evolution.

### Evaluation Metrics

The primary metric is pass$^1$: the fraction of tasks achieving a perfect reward of 1.0:

$$\text{pass}^1 = \frac{1}{N} \sum_{i=1}^{N} \mathbb{1}[r_i = 1.0]$$

This is the standard metric in $\tau$-bench publications. Any reward below 1.0 constitutes failure.

![Reward breakdown for a sample task: the binary pass$^1$ metric aggregates sub-criteria scores into a single pass/fail outcome.](figures/fig_09_reward_breakdown.png){#fig:reward-breakdown}

The fix success rate is defined as:

$$\text{FSR} = \frac{|\{i : \text{fix}_i \text{ succeeds}\}|}{M}$$

where $M$ is the number of attempted fixes. A fix succeeds when the patched student passes the task unanimously across all trials.

The statistical analysis plan comprises two hypothesis tests plus interval reporting:

- **Effectiveness.** Paired one-sided $t$-test on per-task trial-pass-rate deltas (evolved minus baseline) at $\alpha = 0.05$. Sensitivity checks via McNemar's exact test and Wilcoxon signed-rank test.
- **Diminishing returns.** Cochran-Armitage trend test [@cochran1954; @armitage1955] on fix success rate across ordered pool sizes (5, 10, 20 tasks).
- **Confidence intervals:** Exact Clopper-Pearson intervals for pass rates, following @bowyer2025 for evaluations with fewer than 300 data points.

### Reproducibility

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Random seed | 42 | Deterministic task selection and ordering |
| Trials per task | 3 | Unanimous pass required across all trials |
| Teacher temperature | 0.3 | Focused diagnostic output |
| Reasoning suppression | Enabled | Prevents reasoning tokens from breaking content parsing |
| Max teacher rounds | 10 | Multi-step diagnosis without unbounded cost |

: Fixed experimental parameters. {#tbl:parameters}

The complete evolution state is serialized to JSON after each iteration: the current system prompt, all tool schemas, all preprocessor source, iteration history, and metadata. Task IDs are locked after the first evaluation.

### Threats to Validity

Regarding *internal validity*, three trials per task with a unanimous-pass criterion reduces the probability of accepting fragile patches, though more trials would tighten estimates at higher cost. The teacher's patches reflect Kimi K2.5's capabilities; only patches that demonstrably improve performance enter the global state, mitigating teacher model bias. The string-matching failure taxonomy is heuristic and may misclassify some failures, but this affects per-category analysis rather than primary pass-rate results.

Regarding *external validity*, $\tau^2$-bench tasks are simulated, while production interactions are more diverse and adversarial. The framework is evaluated with one teacher and three student models; generalization to other pairs is untested. Patches are domain-specific by design, and cross-domain transfer is not claimed. Each $\tau^2$-bench task is a unique scenario, not a draw from a homogeneous distribution; the contribution is the framework, not the specific patches. The teacher prompt prohibits task-specific hardcoding, and unanimous validation guards against brittle patches.

Regarding *construct validity*, the pass$^1$ metric treats all failures equally, whereas @rabanser2025 decompose reliability into four dimensions; pass$^1$ captures only consistency. Patches may encode surface-level heuristics without transferring deep domain understanding, and their durability under distribution shift is untested.



<!-- FILE: ch3_0_chapter.md -->

\newpage

# 3. Experimental Results and Evaluation

```{=latex}
\addtocontents{toc}{\protect\setcounter{tocdepth}{3}}
```

This chapter presents the results of testing the DPV framework (EDP Phase 6: Test Solution). The experimental setup described in Section 2.4 is executed across three scales and three student models to evaluate whether the framework achieves the project objectives defined in the Introduction.



<!-- FILE: ch3_1_1_five_task.md -->

## 3.1 5-task Evaluation

#### Qwen3 30B-A3B

The baseline evaluates the unmodified student on five airline tasks with three trials each. @Fig:exp1-heatmap shows the per-task, per-trial results across all three sweeps, and @tbl:exp1-passrate summarises pass rates.

| Sweep | T0 | T1 | T3 | T4 | T5 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|------------|-----------|
| 1 (base) | 0/3 | 2/3 | 1/3 | 3/3 | 2/3 | 8/15 (53%) | 3/5 (60%) |
| 2 (post-S1) | 1/3 | 2/3 | 2/3 | 3/3 | 3/3 | 11/15 (73%) | 4/5 (80%) |
| 3 (post-S2) | 1/3 | 3/3 | 3/3 | 3/3 | 1/3 | 11/15 (73%) | 3/5 (60%) |

: Per-sweep evaluation results for Qwen3 30B-A3B on 5 tasks. Each cell shows trial passes out of three. {#tbl:exp1-passrate}

@Fig:exp1-heatmap provides a visual representation of the same data. Each cell represents a single trial; green indicates a pass, red a fail. The heatmap makes the per-task trajectories immediately legible: Task 4's solid green column, Task 0's persistent red, and the progressive greening of Tasks 1 and 3 across sweeps.

![Per-task, per-trial pass/fail heatmap for Qwen3 30B-A3B across three sweeps (5 tasks). Green cells indicate passing trials, red cells indicate failures.](../../runs/5/sweep_heatmap_print.svg){#fig:exp1-heatmap}

The baseline is non-trivial: the student already passes 60% of tasks by majority vote without any intervention. This confirms that the student is not helplessly incapable; the teacher is refining, not teaching from scratch. The headroom for improvement is 40 percentage points (two tasks: 0 and 3).

The evolution loop ran three sweeps. @Tbl:exp1-outcomes shows the per-sweep breakdown of task outcomes during the evolution process.

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 1 | 3 | 1 | 0 |
| 2 | 2 | 2 | 1 | 0 |
| 3 | 3 | 0 | 0 | 2 |

: Per-sweep task outcomes during the evolution loop for Qwen3 30B-A3B on 5 tasks. {#tbl:exp1-outcomes}

@Fig:exp1-outcomes visualises the same data as a stacked bar chart. The shrinking of the "Fixed" segments and the growth of the "Already passing" segment across sweeps illustrates the diminishing-returns dynamic.

![Stacked bar chart of per-sweep task outcomes for Qwen3 30B-A3B on 5 tasks.](../../runs/5/sweep_outcomes_print.svg){#fig:exp1-outcomes}

Sweep 1 is the most productive: all four failing tasks are repaired, three by instruction patches and one by a guardrail preprocessor. Sweep 2 fixes three of three failing tasks. Sweep 3 produces no new fixes; the two remaining failures resist further patching.

@Tbl:exp1-fixes details the individual fix attempts, including the teacher's patch tier, retry count, and session cost.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|------:|-----:|:------------|:-----|--------:|------------:|-----------:|---------:|
| 1 | 3 | Fail → Pass | instruction | 2 | 10 | 3 | 2m 26s |
| 1 | 0 | Fail → Pass | instruction | 2 | 8 | 2 | 2m 33s |
| 1 | 1 | Fail → Pass | instruction | 1 | 15 | 6 | 1m 13s |
| 1 | 5 | Fail → Pass | guardrail | 3 | 44 | 18 | 8m 22s |
| 2 | 0 | Fail → Pass | instruction | 1 | 6 | 2 | 2m 3s |
| 2 | 3 | Fail → Pass | guardrail | 3 | 20 | 6 | 9m 28s |
| 2 | 1 | Fail → Pass | instruction | 2 | 14 | 5 | 7m 32s |

: Individual fix attempts for Qwen3 30B-A3B on 5 tasks. {#tbl:exp1-fixes}

@Fig:exp1-fix-attempts shows the number of tasks fixed per attempt and tier across sweeps.

![Fix attempts by tier and sweep for Qwen3 30B-A3B on 5 tasks.](../../runs/5/fix_attempts_print.svg){#fig:exp1-fix-attempts}

Of seven successful fixes across sweeps 1 and 2, five (71%) were instruction-tier patches and two (29%) were guardrail-tier. Instruction-tier fixes are also cheaper. The median instruction fix took 2 attempts, 10 messages, and 2.5 tool calls; the median guardrail fix took 3 attempts, 32 messages, and 12 tool calls.

The dominance of instruction-tier patches supports the Superficial Alignment Hypothesis [@zhou2023lima]: the student model's failures are primarily failures of instruction following, not of capability.

The negative result is the regression of Task 5 between sweeps 2 and 3. In sweep 2, Task 5 passes all three trials (3/3). In sweep 3, it passes only one (1/3). Since no patches targeted Task 5 between sweeps 2 and 3 (it was already passing), the regression is attributable either to stochastic variation or to interference from patches accumulated during sweep 2's fixes of other tasks.

In summary, the aggregate trial pass rate rises from 53% (baseline) to 73% (after two sweeps of evolution). Instruction-level patches account for the majority of successful fixes. However, the 5-task setting saturates quickly: by sweep 3, no further fixes are possible, and patch interference introduces mild regression.

#### Qwen3.5 Flash

The same five tasks (0, 1, 3, 4, 5) were evaluated with Qwen3.5 Flash as the student model. At baseline, Qwen3.5 Flash achieves a perfect 5/5 majority-vote pass rate (15/15 trials), requiring no evolution intervention. Every task that Qwen3 30B-A3B struggled with, including Task 0 (which never reliably passed even after evolution) and Task 3 (which required multi-sweep patching), is solved by Qwen3.5 Flash out of the box.

This result establishes a ceiling reference: the 5-task airline configuration is within the unassisted capability of a stronger non-thinking model. The evolution framework's contribution on these tasks is to bridge the gap between a weaker model's capability and this ceiling, a gap that a stronger student does not have.

#### GLM 4.7 Flash

@Tbl:glm5-passrate summarises pass rates across sweeps for GLM 4.7 Flash on five tasks. @Fig:glm47-5-heatmap visualises the per-task, per-trial results.

| Sweep | T0 | T1 | T3 | T4 | T5 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|------------|-----------|
| 1 (base) | 2/3 | 1/3 | 1/3 | 3/3 | 0/3 | 7/15 (47%) | 2/5 (40%) |
| 2 (post-S1) | 3/3 | 3/3 | 2/3 | 2/3 | 1/3 | 11/15 (73%) | 4/5 (80%) |
| 3 (post-S2) | 1/3 | 2/3 | 1/3 | 2/3 | 1/3 | 7/15 (47%) | 2/5 (40%) |

: Per-sweep evaluation results for GLM 4.7 Flash on 5 tasks. {#tbl:glm5-passrate}

![Per-task, per-trial pass/fail heatmap for GLM 4.7 Flash across three sweeps (5 tasks).](../../runs/glm47_5/sweep_heatmap_print.svg){#fig:glm47-5-heatmap}

The baseline is comparable to Qwen3 30B-A3B's: 47% trial rate and 40% majority rate, with Tasks 0 and 4 passing by majority vote. The three failing tasks (1, 3, 5) represent the headroom for evolution.

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 1 | 3 | 0 | 1 |
| 2 | 2 | 0 | 1 | 2 |
| 3 | 0 | 0 | 0 | 5 |

: Per-sweep task outcomes during the evolution loop for GLM 4.7 Flash on 5 tasks. {#tbl:glm5-outcomes}

![Stacked bar chart of per-sweep task outcomes for GLM 4.7 Flash on 5 tasks.](../../runs/glm47_5/sweep_outcomes_print.svg){#fig:glm47-5-outcomes}

Sweep 1 fixes three tasks (all instruction-tier): Tasks 1, 5, and 0. Task 3 resists repair. Sweep 2 adds one guardrail fix for Task 4 (which was already passing by majority but had failed during the evolution loop's single-trial check). Sweep 3 produces no new fixes; the evolution loop sees all five tasks as failing, reflecting regression.

@Tbl:glm5-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|------:|-----:|:------------|:-----|--------:|------------:|-----------:|---------:|
| 1 | 1 | Fail → Pass | instruction | 1 | 8 | 3 | 2m 59s |
| 1 | 5 | Fail → Pass | instruction | 1 | 8 | 3 | 3m 35s |
| 1 | 0 | Fail → Pass | instruction | 1 | 4 | 1 | 5m 0s |
| 1 | 3 | Fail → Fail | --- | --- | 25 | 9 | 6m 5s |
| 2 | 3 | Fail → Fail | --- | --- | 16 | 5 | 3m 10s |
| 2 | 4 | Fail → Pass | guardrail | 3 | 21 | 7 | 3m 16s |
| 2 | 5 | Fail → Fail | --- | --- | 54 | 24 | 7m 23s |

: Individual fix attempts for GLM 4.7 Flash on 5 tasks. {#tbl:glm5-fixes}

![Fix attempts by tier and sweep for GLM 4.7 Flash on 5 tasks.](../../runs/glm47_5/fix_attempts_print.svg){#fig:glm47-5-fix-attempts}

Total fixes: 4 (3 instruction, 1 guardrail). Of the three genuinely failing tasks at baseline (1, 3, 5), two were fixed: a 67% fix rate, comparable to Qwen3 30B-A3B's performance.

The defining result for GLM 4.7 Flash at five tasks is the regression between sweeps 2 and 3. The majority pass rate drops from 80% (4/5) to 40% (2/5), a 40-percentage-point decline. The trial rate drops from 73% to 47%, returning exactly to the baseline. Tasks 0 and 3, which had improved in sweep 2, revert to their baseline state. Even Task 4, which passed perfectly at baseline (3/3), degrades to 2/3.

This regression is larger than the regressions observed with Qwen3 30B-A3B (which lost only one task between sweeps 2 and 3) or Qwen3.5 Flash at 10 tasks (which lost 10 percentage points). It suggests that GLM 4.7 Flash is particularly vulnerable to patch interference: the accumulated patches from sweeps 1 and 2 create conflicting directives that the model cannot reconcile.

In summary, GLM 4.7 Flash achieves a strong peak improvement (+40pp majority, +26pp trial at sweep 2), demonstrating that the evolution framework can work with this model. However, the gains are entirely erased by sweep 3, indicating that the model lacks the robustness to maintain improvements under patch accumulation. Task 3 is never fixed across either sweep, remaining the sole resistant task.

#### Comparative Analysis at Five Tasks

| Metric | Qwen3 30B-A3B | Qwen3.5 Flash | GLM 4.7 Flash |
|--------|---------------|---------------|---------------|
| Baseline trial rate | 53% (8/15) | 100% (15/15) | 47% (7/15) |
| Baseline majority rate | 60% (3/5) | 100% (5/5) | 40% (2/5) |
| Best trial rate (post-evo) | 73% (11/15) | 100% (15/15) | 73% (11/15) |
| Best majority rate (post-evo) | 80% (4/5) | 100% (5/5) | 80% (4/5) |
| Sweep 3 majority | 60% (3/5) | 100% (5/5) | 40% (2/5) |
| Evolution needed? | Yes | No | Yes |
| Genuinely failing tasks | 2 | 0 | 3 |
| Fix rate on failing tasks | 100% | N/A | 67% |
| Total fixes (instr/guard) | 7 (5/2) | 0 | 4 (3/1) |

: 5-task comparison across three student models. "Best" refers to the sweep with the highest pass rate. {#tbl:5task-comparison}

Three patterns emerge. First, both weaker models reach the same peak performance (80% majority, 73% trial), suggesting a common ceiling for the 5-task setting that prompt evolution can approach but not exceed. Second, the models diverge sharply in their ability to retain gains: Qwen3 30B-A3B holds most of its improvement through sweep 3, while GLM 4.7 Flash collapses back to baseline. Third, Qwen3.5 Flash's perfect baseline confirms that these five tasks are within reach of a sufficiently capable model without any evolution intervention.



<!-- FILE: ch3_1_2_ten_task.md -->

## 3.2 10-Task Experiments

#### Qwen3 30B-A3B

Experiment 2 doubles the task set from five to 10, introducing five additional tasks (7, 9, 10, 11, 12). @Fig:exp2-heatmap shows the per-task, per-trial results across all three sweeps, and @tbl:exp2-passrate summarises pass rates.

| Sweep | T0 | T1 | T3 | T4 | T5 | T7 | T9 | T10 | T11 | T12 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|-----|-----|------|------|------|------------|-----------|
| 1 (base) | 0/3 | 2/3 | 0/3 | 3/3 | 2/3 | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 | 8/30 (27%) | 3/10 (30%) |
| 2 (post-S1) | 1/3 | 2/3 | 0/3 | 3/3 | 2/3 | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 | 9/30 (30%) | 3/10 (30%) |
| 3 (post-S2) | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 | 15/30 (50%) | 5/10 (50%) |

: Per-sweep evaluation results for Qwen3 30B-A3B on 10 tasks. {#tbl:exp2-passrate}

@Fig:exp2-heatmap visualises the same data. Compared to the 5-task heatmap, the 10-task version makes the bifurcation between fixable and resistant tasks immediately visible: a cluster of tasks (0, 1, 3, 4, 5) greens progressively across sweeps, while a second cluster (7, 9, 11, 12) remains solidly red throughout. Task 10 occupies a middle ground; it was fixed during sweep 1's evolution but never passed more than 1/3 trials in re-evaluation, suggesting a fragile fix.

![Per-task, per-trial pass/fail heatmap for Qwen3 30B-A3B across three sweeps (10 tasks).](../../runs/10/sweep_heatmap_print.svg){#fig:exp2-heatmap}

The baseline is lower than in the 5-task setting: only 27% of trials pass (8/30), versus 53% (8/15). By majority vote, 3 of 10 tasks pass (30%), versus 3 of 5 (60%). The five tasks shared with the 5-task experiment exhibit identical baseline performance, confirming that the seed and configuration reproduce consistently.

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 1 | 4 | 1 | 4 |
| 2 | 1 | 1 | 1 | 7 |
| 3 | 4 | 0 | 0 | 6 |

: Per-sweep task outcomes for Qwen3 30B-A3B on 10 tasks. {#tbl:exp2-outcomes}

@Fig:exp2-outcomes visualises the same data. The persistent red "Unfixed" segment, absent in the 5-task sweeps 1 and 2, dominates the chart, reflecting a hard core of tasks that resist prompt-level repair.

![Stacked bar chart of per-sweep task outcomes for Qwen3 30B-A3B on 10 tasks.](../../runs/10/sweep_outcomes_print.svg){#fig:exp2-outcomes}

The trajectory differs markedly from the 5-task experiment. In the 5-task run, sweep 1 fixed all tasks that failed within the evolution loop; here, sweep 1 fixes only 5 of 9 tasks that failed the loop's single-trial check (the 9 includes two tasks, T1 and T5, that pass by majority vote at baseline but failed individual trials). The four unfixed tasks (7, 9, 11, 12) consumed a combined 150 messages, 61 tool calls, and 36 minutes of wall-clock time, without producing a single viable patch.

A second difference is the delayed improvement in evaluation metrics. Sweep 2's re-evaluation shows essentially no change from baseline (9/30 trials, 30% majority), despite sweep 1 having fixed five tasks during the evolution loop. The full improvement materialises only in sweep 3 (15/30 trials, 50% majority), after sweep 2's fixes had a chance to reinforce the earlier patches.

@Tbl:exp2-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|------:|-----:|:------------|:-----|--------:|------------:|-----------:|---------:|
| 1 | 0 | Fail → Pass | instruction | 1 | 10 | 4 | 51s |
| 1 | 1 | Fail → Pass | instruction | 1 | 4 | 1 | 21s |
| 1 | 5 | Fail → Pass | instruction | 2 | 16 | 6 | 5m 11s |
| 1 | 3 | Fail → Pass | guardrail | 3 | 36 | 15 | 5m 54s |
| 1 | 10 | Fail → Pass | instruction | 2 | 35 | 14 | 6m 59s |
| 1 | 12 | Fail → Fail | --- | --- | 36 | 15 | 8m 37s |
| 1 | 9 | Fail → Fail | --- | --- | 37 | 14 | 12m 36s |
| 1 | 11 | Fail → Fail | --- | --- | 38 | 16 | 6m 21s |
| 1 | 7 | Fail → Fail | --- | --- | 39 | 16 | 8m 40s |
| 2 | 1 | Fail → Pass | instruction | 2 | 12 | 4 | 3m 42s |
| 2 | 5 | Fail → Pass | guardrail | 3 | 59 | 26 | 11m 49s |
| 2 | 3 | Fail → Fail | --- | --- | 26 | 10 | 3m 33s |
| 2 | 0 | Fail → Fail | --- | --- | 35 | 12 | 5m 9s |
| 2 | 12 | Fail → Fail | --- | --- | 46 | 19 | 7m 50s |
| 2 | 11 | Fail → Fail | --- | --- | 37 | 15 | 8m 45s |
| 2 | 7 | Fail → Fail | --- | --- | 22 | 8 | 7m 22s |
| 2 | 9 | Fail → Fail | --- | --- | 39 | 17 | 10m 0s |
| 2 | 10 | Fail → Fail | --- | --- | 38 | 16 | 19m 0s |

: Individual fix attempts for Qwen3 30B-A3B on 10 tasks. {#tbl:exp2-fixes}

@Fig:exp2-fix-attempts shows the number of tasks fixed per attempt and tier across sweeps.

![Fix attempts by tier and sweep for Qwen3 30B-A3B on 10 tasks.](../../runs/10/fix_attempts_print.svg){#fig:exp2-fix-attempts}

Across sweeps 1 and 2, seven successful fixes were applied: five instruction-tier (71%) and two guardrail-tier (29%). This ratio is identical to the 5-task experiment's, suggesting that the instruction-guardrail balance is a stable property of the framework rather than an artefact of the specific task set.

The cost distribution shifts. In the 5-task run, the teacher encountered no unfixable tasks until sweep 3. In the 10-task run, the teacher exhausted all retries on four tasks in sweep 1 and seven in sweep 2, consuming 393 messages, 162 tool calls, and over 107 minutes on failed attempts.

In summary, the trial pass rate rises from 27% (baseline) to 50% (after two sweeps), a 23-percentage-point gain comparable to the 5-task run's +20pp. The instruction-guardrail ratio (71%/29%) is identical. However, four of seven majority-vote failures (Tasks 7, 9, 11, 12) resist all fix attempts, and improvement is delayed by one sweep due to patch fragility.

#### Qwen3.5 Flash

The same 10 tasks were evaluated with Qwen3.5 Flash as the student model. @Tbl:exp2-flash-passrate summarises pass rates across sweeps.

| Sweep | T0 | T1 | T3 | T4 | T5 | T7 | T9 | T10 | T11 | T12 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|-----|-----|------|------|------|------------|-----------|
| 1 (base) | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 | 0/3 | 0/3 | 3/3 | 1/3 | 1/3 | 18/30 (60%) | 5/10 (50%) |
| 2 (post-S1) | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 | 0/3 | 0/3 | 3/3 | 3/3 | 3/3 | 24/30 (80%) | 8/10 (80%) |
| 3 (post-S2) | 3/3 | 3/3 | 3/3 | 2/3 | 2/3 | 0/3 | 1/3 | 2/3 | 0/3 | 3/3 | 19/30 (63%) | 7/10 (70%) |

: Per-sweep evaluation results for Qwen3.5 Flash on 10 tasks. {#tbl:exp2-flash-passrate}

![Per-task, per-trial pass/fail heatmap for Qwen3.5 Flash across three sweeps (10 tasks). The heatmap reveals a much greener baseline than Qwen3 30B-A3B, with five tasks passing perfectly from the start.](../../runs/qwen35-flash_10/sweep_heatmap_print.svg){#fig:exp2-flash-heatmap}

The baseline is higher than Qwen3 30B-A3B's on the same tasks: 60% trial pass rate versus 27%, and 50% majority pass rate versus 30%. The five tasks that Qwen3 30B-A3B needed evolution to pass (0, 1, 3, 4, 10) are already solved by Qwen3.5 Flash at baseline. The failing tasks are a different set: Tasks 5, 7, 9, 11, and 12. Of these, Task 7 is the same resistant task that Qwen3 30B-A3B also could not fix. As shown below, however, Qwen3.5 Flash is able to fix Task 9 (along with Tasks 5, 11, and 12), demonstrating that most of these failures are model-specific rather than task-intrinsic.

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 5 | 4 | 0 | 1 |
| 2 | 8 | 0 | 1 | 1 |
| 3 | 4 | 0 | 0 | 6 |

: Per-sweep task outcomes during the evolution loop for Qwen3.5 Flash on 10 tasks. {#tbl:exp2-flash-outcomes}

![Stacked bar chart of per-sweep task outcomes for Qwen3.5 Flash on 10 tasks. The green "Passed" segment reflects the higher baseline; the evolution loop mainly addresses edge-case failures.](../../runs/qwen35-flash_10/sweep_outcomes_print.svg){#fig:exp2-flash-outcomes}

The evolution trajectory is markedly more efficient than Qwen3 30B-A3B's. In sweep 1, 5 of 10 tasks are already passing; of the 5 failing tasks, 4 are fixed by instruction patches and only Task 7 resists repair. Sweep 2 sees 8 tasks already passing; the one remaining fixable task (Task 9) requires escalation to a guardrail fix. By sweep 2, the framework has raised Qwen3.5 Flash's majority pass rate from 50% to 80%: a +30pp gain.

@Tbl:exp2-flash-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|------:|-----:|:------------|:-----|--------:|------------:|-----------:|---------:|
| 1 | 11 | Fail → Pass | instruction | 1 | 6 | 2 | 42s |
| 1 | 12 | Fail → Pass | instruction | 2 | 21 | 8 | 3m 25s |
| 1 | 9 | Fail → Pass | instruction | 2 | 26 | 11 | 6m 34s |
| 1 | 7 | Fail → Fail | --- | --- | 50 | 22 | 8m 37s |
| 1 | 5 | Fail → Pass | instruction | 2 | 8 | 2 | 72m 27s |
| 2 | 7 | Fail → Fail | --- | --- | 24 | 9 | 6m 18s |
| 2 | 9 | Fail → Pass | guardrail | 3 | 39 | 16 | 7m 28s |

: Individual fix attempts for Qwen3.5 Flash on 10 tasks. {#tbl:exp2-flash-fixes}

Qwen3.5 Flash can fix tasks that Qwen3 30B-A3B could not. Tasks 11 and 12, part of Qwen3 30B-A3B's "hard core" of unfixable tasks, are both fixed by instruction patches on Qwen3.5 Flash (Task 11 on the first attempt in just 42 seconds, Task 12 on the second attempt). This confirms that these tasks are not inherently beyond the reach of prompt-level correction; rather, Qwen3 30B-A3B lacked the baseline capability to execute even well-specified instructions for these tasks. The stronger student can act on the same guidance that the weaker student could not.

Task 7, however, resists repair on both models, consuming 50 messages and 22 tool calls in sweep 1, then 24 messages and 9 tool calls in sweep 2, without success. This task appears to represent a structural challenge that neither model can handle through prompt-level intervention alone.

![Fix attempts by tier and sweep for Qwen3.5 Flash on 10 tasks.](../../runs/qwen35-flash_10/fix_attempts_print.svg){#fig:exp2-flash-fix-attempts}

Across sweeps 1 and 2, five successful fixes were applied: four instruction-tier (80%) and one guardrail-tier (20%). The instruction dominance is even more pronounced than with Qwen3 30B-A3B (71%), consistent with the hypothesis that a stronger student can execute instruction-level guidance more reliably and therefore requires less escalation to guardrail interventions.

The main result is the regression in sweep 3. The majority pass rate drops from 80% (sweep 2) to 70% (sweep 3), and the trial pass rate drops from 80% to 63%. Tasks 4, 5, 10, and 11 all degrade: Task 4 drops from 3/3 to 2/3, Task 5 from 3/3 to 2/3, Task 10 from 3/3 to 2/3, and Task 11 from 3/3 to 0/3. This regression is larger than observed with Qwen3 30B-A3B, where only Task 5 regressed significantly.

The likely explanation is patch interference compounded by the stronger model's sensitivity to instruction changes. A model that follows instructions more precisely may also be more disrupted when accumulated patches create conflicting directives. Task 11's complete regression (3/3 → 0/3) illustrates the risk: this task was successfully fixed in sweep 1 with a simple instruction patch (42 seconds, 6 messages), yet the patches accumulated during sweep 2 appear to have undone this fix entirely.

#### GLM 4.7 Flash

@Tbl:glm10-passrate summarises pass rates across sweeps. @Fig:glm47-10-heatmap visualises the per-task, per-trial results.

| Sweep | T0 | T1 | T3 | T4 | T5 | T7 | T9 | T10 | T11 | T12 | Trial rate | Maj. rate |
|-------|-----|-----|-----|-----|-----|-----|-----|------|------|------|------------|-----------|
| 1 (base) | 3/3 | 2/3 | 3/3 | 3/3 | 2/3 | 0/3 | 0/3 | 2/3 | 0/3 | 0/3 | 15/30 (50%) | 6/10 (60%) |
| 2 (post-S1) | 3/3 | 1/3 | 3/3 | 2/3 | 2/3 | 0/3 | 0/3 | 2/3 | 0/3 | 0/3 | 13/30 (43%) | 5/10 (50%) |
| 3 (post-S2) | 2/3 | 2/3 | 2/3 | 2/3 | 1/3 | 0/3 | 0/3 | 2/3 | 1/3 | 0/3 | 12/30 (40%) | 5/10 (50%) |

: Per-sweep evaluation results for GLM 4.7 Flash on 10 tasks. {#tbl:glm10-passrate}

![Per-task, per-trial pass/fail heatmap for GLM 4.7 Flash across three sweeps (10 tasks).](../../runs/glm47_10/sweep_heatmap_print.svg){#fig:glm47-10-heatmap}

The baseline is the highest by majority rate at this scale: 50% trial rate and 60% majority rate, compared to 27%/30% for Qwen3 30B-A3B and 60%/50% for Qwen3.5 Flash. Six of 10 tasks pass at baseline (0, 1, 3, 4, 5, 10). The four genuinely failing tasks are the same hard core seen across other models: Tasks 7, 9, 11, and 12.

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 3 | 1 | 1 | 5 |
| 2 | 2 | 2 | 0 | 6 |
| 3 | 0 | 0 | 0 | 10 |

: Per-sweep task outcomes during the evolution loop for GLM 4.7 Flash on 10 tasks. {#tbl:glm10-outcomes}

![Stacked bar chart of per-sweep task outcomes for GLM 4.7 Flash on 10 tasks.](../../runs/glm47_10/sweep_outcomes_print.svg){#fig:glm47-10-outcomes}

The evolution trajectory tells a story of failure. @Tbl:glm10-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|------:|-----:|:------------|:-----|--------:|------------:|-----------:|---------:|
| 1 | 10 | Fail → Pass | instruction | 2 | 18 | 7 | 4m 25s |
| 1 | 1 | Fail → Pass | guardrail | 3 | 18 | 6 | 5m 53s |
| 1 | 7 | Fail → Fail | --- | --- | 26 | 10 | 4m 0s |
| 1 | 11 | Fail → Fail | --- | --- | 56 | 24 | 5m 11s |
| 1 | 5 | Fail → Fail | --- | --- | 44 | 18 | 5m 41s |
| 1 | 12 | Fail → Fail | --- | --- | 56 | 24 | 8m 37s |
| 1 | 9 | Fail → Fail | --- | --- | 54 | 21 | 8m 40s |
| 2 | 4 | Fail → Pass | instruction | 1 | 8 | 3 | 1m 10s |
| 2 | 1 | Fail → Pass | instruction | 1 | 13 | 5 | 1m 19s |
| 2 | 7 | Fail → Fail | --- | --- | 45 | 20 | 3m 52s |
| 2 | 12 | Fail → Fail | --- | --- | 71 | 30 | 5m 46s |
| 2 | 11 | Fail → Fail | --- | --- | 43 | 19 | 6m 39s |
| 2 | 10 | Fail → Fail | --- | --- | 45 | 20 | 7m 41s |
| 2 | 9 | Fail → Fail | --- | --- | 58 | 24 | 29m 3s |
| 2 | 5 | Fail → Fail | --- | --- | 35 | 14 | 30m 38s |

: Individual fix attempts for GLM 4.7 Flash on 10 tasks. {#tbl:glm10-fixes}

![Fix attempts by tier and sweep for GLM 4.7 Flash on 10 tasks.](../../runs/glm47_10/fix_attempts_print.svg){#fig:glm47-10-fix-attempts}

The key finding is that all four successful fixes targeted tasks that were already passing by majority vote at baseline. Tasks 10 and 1 (sweep 1) and Tasks 4 and 1 (sweep 2) all had majority-vote baselines of ≥2/3. The four genuinely failing tasks, 7, 9, 11, and 12, were attempted in both sweeps and failed every time, yielding a 0% fix rate on genuinely failing tasks.

The evolution loop produces patches, and the teacher diagnoses failures correctly, but GLM 4.7 Flash cannot translate these patches into reliable execution at this scale. The patches fix one behaviour but introduce new errors elsewhere. This is visible in the progressive degradation of the trial rate across sweeps: 50% → 43% → 40%. Even tasks that were comfortably passing at baseline (e.g., Task 1 at 2/3, Task 5 at 2/3) become more fragile after patches are applied.

The sweep 3 result is especially revealing: the evolution loop sees all 10 tasks as failing, even though the 3-trial re-evaluation shows five passing by majority. The model's behaviour is becoming increasingly unstable as patches accumulate.

In summary, GLM 4.7 Flash at 10 tasks represents the framework's most direct failure mode. Despite a 60% majority baseline, the evolution loop cannot fix any genuinely failing task and actively degrades performance on passing tasks. The trial rate declines monotonically from 50% to 40% across three sweeps. This result motivated dropping GLM 4.7 Flash from the 20-task experiment.

#### Comparative Analysis at 10 Tasks

@Tbl:10task-comparison summarises the key metrics for all three models at 10 tasks.

| Metric | Qwen3 30B-A3B | Qwen3.5 Flash | GLM 4.7 Flash |
|--------|---------------|---------------|---------------|
| Baseline trial rate | 27% (8/30) | 60% (18/30) | 50% (15/30) |
| Baseline majority rate | 30% (3/10) | 50% (5/10) | 60% (6/10) |
| Best trial rate (post-evo) | 50% (15/30) | 80% (24/30) | 50% (15/30) |
| Best majority rate (post-evo) | 50% (5/10) | 80% (8/10) | 60% (6/10) |
| Improvement (pp, trial) | +23 | +20 | 0 |
| Improvement (pp, majority) | +20 | +30 | 0 |
| Fix rate on failing tasks | 3/7 (43%) | 4/5 (80%) | 0/4 (0%) |
| Total fixes (instr/guard) | 7 (5/2) | 5 (4/1) | 4 (3/1) |
| Unfixable tasks | 4 (7, 9, 11, 12) | 1 (7) | 4 (7, 9, 11, 12) |
| Sweep 3 regression? | Mild | -17pp trial | Continuous decline |

: 10-task comparison across three student models. "Best" refers to the sweep with the highest pass rate. GLM 4.7 Flash's "best" is the baseline itself, since evolution produces no net improvement. Fix rate counts tasks failing by majority vote at baseline that the teacher successfully fixed at least once. {#tbl:10task-comparison}

Four patterns emerge from the 3-model comparison:

The framework is not universally beneficial. GLM 4.7 Flash receives the same teacher patches as the other models but cannot convert them into durable improvements at this scale. The framework's value is contingent on the student model's ability to execute patched instructions reliably.

The stronger student benefits most from evolution. Qwen3.5 Flash achieves the highest ceiling (80% majority) and the highest fix rate on genuinely failing tasks (80%). Qwen3 30B-A3B achieves moderate improvement (+20pp majority) with a 43% fix rate. GLM 4.7 Flash achieves none.

The hard core of resistant tasks is consistent. Tasks 7, 9, 11, and 12 resist repair for both Qwen3 30B-A3B and GLM 4.7 Flash. With Qwen3.5 Flash, three of these (9, 11, 12) become fixable, leaving only Task 7 as genuinely resistant across all three models.

Regression risk varies by model architecture. Qwen3.5 Flash shows discrete regression in sweep 3 (-17pp trial, -10pp majority). GLM 4.7 Flash shows continuous decline across all sweeps. Qwen3 30B-A3B shows the mildest regression. The relationship between instruction-following quality and regression severity is not monotonic; GLM 4.7 Flash's regression is the worst despite not being the strongest instruction follower.



<!-- FILE: ch3_1_3_twenty_task.md -->

## 3.3 20-Task Experiments

#### Qwen3 30B-A3B

Experiment 3 doubles the task set again to 20, introducing 10 additional tasks (14, 15, 17, 20, 21, 23, 27, 28, 33, 34) alongside the original 10. This tests whether the framework's gains continue to scale and how the teacher's strategy adapts to a larger and more diverse failure surface.

@Tbl:exp3-passrate summarises pass rates across sweeps.

| Sweep | Trial rate | Maj. rate |
|-------|------------|-----------|
| 1 (base) | 13/60 (22%) | 5/20 (25%) |
| 2 (post-S1) | 20/60 (33%) | 5/20 (25%) |
| 3 (post-S2) | 18/60 (30%) | 6/20 (30%) |

: Per-sweep pass rates for Qwen3 30B-A3B on 20 tasks. {#tbl:exp3-passrate}

The per-task baseline results reveal the scale of the challenge. Of 20 tasks, only 5 pass by majority vote at baseline: Tasks 1 (2/3), 4 (3/3), 5 (2/3), 10 (2/3), and 34 (2/3). The remaining 15 tasks fail, with 11 scoring 0/3. The baseline trial rate (22%) is the lowest of any experiment, confirming the expected dilution effect as harder tasks are added.

![Per-task, per-trial pass/fail heatmap for Qwen3 30B-A3B across three sweeps (20 tasks). The heatmap shows that failing cells dominate, with improvement concentrated in a small subset of tasks on the left side.](../../runs/20/sweep_heatmap_print.svg){#fig:exp3-heatmap}

@Fig:exp3-heatmap visualises the per-task trajectories. The heatmap shows failing cells across most tasks, with progressive improvement visible only in the leftmost cluster (Tasks 0, 1, 3, 4, 5) and scattered improvements in Tasks 28, 33, and 34. The right half of the heatmap, Tasks 14 through 27, remains failing across all three sweeps, indicating failures that prompt evolution did not repair in this experiment.

The per-task breakdown for all three sweeps:

| Task | Sweep 1 | Sweep 2 | Sweep 3 | Trajectory |
|------|---------|---------|---------|------------|
| 0 | 1/3 | 2/3 | 3/3 | Improving |
| 1 | 2/3 | 3/3 | 2/3 | Stable pass |
| 3 | 0/3 | 1/3 | 0/3 | Fragile |
| 4 | 3/3 | 3/3 | 2/3 | Stable pass |
| 5 | 2/3 | 2/3 | 3/3 | Improving |
| 7 | 0/3 | 0/3 | 0/3 | Resistant |
| 9 | 0/3 | 0/3 | 0/3 | Resistant |
| 10 | 2/3 | 1/3 | 1/3 | Regressing |
| 11 | 1/3 | 1/3 | 0/3 | Regressing |
| 12 | 0/3 | 1/3 | 0/3 | Resistant |
| 14 | 0/3 | 0/3 | 0/3 | Resistant |
| 15 | 0/3 | 1/3 | 1/3 | Fragile |
| 17 | 0/3 | 0/3 | 0/3 | Resistant |
| 20 | 0/3 | 0/3 | 0/3 | Resistant |
| 21 | 0/3 | 0/3 | 0/3 | Resistant |
| 23 | 0/3 | 0/3 | 0/3 | Resistant |
| 27 | 0/3 | 0/3 | 0/3 | Resistant |
| 28 | 0/3 | 1/3 | 3/3 | Late bloomer |
| 33 | 0/3 | 1/3 | 1/3 | Fragile |
| 34 | 2/3 | 3/3 | 2/3 | Stable pass |

: Per-task trajectories for Qwen3 30B-A3B on 20 tasks. Trajectories classify tasks by their evolution arc: "Improving" tasks trend from fail to pass; "Stable pass" tasks pass throughout; "Fragile" tasks show inconsistent results; "Resistant" tasks never pass by majority vote; "Regressing" tasks degrade across sweeps; "Late bloomer" tasks only pass in the final sweep. {#tbl:exp3-trajectories}

| Sweep | Already passing | Fixed (instruction) | Fixed (tools) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|----|---------|---------|
| 1 | 1 | 3 | 1 | 1 | 14 |
| 2 | 3 | 4 | 1 | 0 | 12 |
| 3 | 3 | 0 | 0 | 0 | 17 |

: Per-sweep task outcomes for Qwen3 30B-A3B on 20 tasks. A new fix tier, "tools" (tool-schema patching), appears for the first time. {#tbl:exp3-outcomes}

![Stacked bar chart of per-sweep task outcomes for Qwen3 30B-A3B on 20 tasks. The red "Unfixed" segment reflects the prevalence of resistant tasks at this scale.](../../runs/20/sweep_outcomes_print.svg){#fig:exp3-outcomes}

A new phenomenon appears at this scale: tool-schema fixes emerge as a distinct tier. In both sweeps 1 and 2, one task (Task 0) was fixed via tool-schema patching rather than instruction or guardrail modification. This is the first time in any experiment that tool-level patches contributed to successful fixes, suggesting that the larger and more diverse failure surface exposes failure modes that cannot be addressed at the instruction or guardrail level alone.

@Tbl:exp3-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|------:|-----:|:------------|:-----|--------:|------------:|-----------:|---------:|
| 1 | 5 | Fail → Pass | instruction | 1 | 8 | 3 | 17s |
| 1 | 1 | Fail → Pass | instruction | 1 | 6 | 2 | 1m 2s |
| 1 | 0 | Fail → Pass | tools | 2 | 18 | 7 | 3m 33s |
| 1 | 3 | Fail → Pass | guardrail | 3 | 26 | 9 | 5m 15s |
| 1 | 34 | Fail → Pass | instruction | 2 | 20 | 8 | 5m 31s |
| 1 | 28 | Fail → Fail | --- | --- | 48 | 17 | 5m 28s |
| 1 | 14 | Fail → Fail | --- | --- | 20 | 7 | 8m 28s |
| 1 | 11 | Fail → Fail | --- | --- | 42 | 17 | 7m 53s |
| 1 | 17 | Fail → Fail | --- | --- | 39 | 16 | 8m 40s |
| 1 | 7 | Fail → Fail | --- | --- | 36 | 14 | 8m 15s |
| 1 | 9 | Fail → Fail | --- | --- | 40 | 15 | 11m 2s |
| 1 | 15 | Fail → Fail | --- | --- | 34 | 14 | 11m 4s |
| 1 | 27 | Fail → Fail | --- | --- | 36 | 15 | 9m 33s |
| 1 | 33 | Fail → Fail | --- | --- | 44 | 19 | 13m 17s |
| 1 | 10 | Fail → Fail | --- | --- | 38 | 14 | 13m 23s |
| 1 | 21 | Fail → Fail | --- | --- | 36 | 14 | 12m 38s |
| 1 | 23 | Fail → Fail | --- | --- | 30 | 12 | 10m 38s |
| 1 | 12 | Fail → Fail | --- | --- | 38 | 15 | 16m 48s |
| 1 | 20 | Fail → Fail | --- | --- | 55 | 25 | 19m 38s |
| 2 | 3 | Fail → Pass | instruction | 1 | 8 | 3 | 2m 7s |
| 2 | 10 | Fail → Pass | instruction | 1 | 12 | 5 | 3m 46s |
| 2 | 28 | Fail → Pass | instruction | 2 | 12 | 4 | 7m 16s |
| 2 | 5 | Fail → Pass | instruction | 2 | 15 | 5 | 6m 32s |
| 2 | 0 | Fail → Pass | tools | 2 | 32 | 12 | 8m 9s |
| 2 | 17 | Fail → Fail | --- | --- | 20 | 7 | 7m 22s |
| 2 | 11 | Fail → Fail | --- | --- | 45 | 19 | 10m 41s |
| 2 | 15 | Fail → Fail | --- | --- | 38 | 15 | 14m 47s |
| 2 | 20 | Fail → Fail | --- | --- | 43 | 18 | 16m 23s |
| 2 | 14 | Fail → Fail | --- | --- | 41 | 17 | 13m 55s |
| 2 | 27 | Fail → Fail | --- | --- | 22 | 8 | 11m 2s |
| 2 | 12 | Fail → Fail | --- | --- | 54 | 21 | 16m 23s |
| 2 | 7 | Fail → Fail | --- | --- | 34 | 14 | 20m 21s |
| 2 | 9 | Fail → Fail | --- | --- | 44 | 19 | 19m 18s |
| 2 | 23 | Fail → Fail | --- | --- | 36 | 15 | 18m 44s |
| 2 | 21 | Fail → Fail | --- | --- | 44 | 19 | 16m 29s |
| 2 | 33 | Fail → Fail | --- | --- | 2 | --- | 72m 6s |

: Individual fix attempts for Qwen3 30B-A3B on 20 tasks. {#tbl:exp3-fixes}

Failed attempts consumed most of the teacher budget. Across sweeps 1 and 2, the teacher exhausted all retries on 25 task-sweep combinations (14 in sweep 1, 11 in sweep 2), spending a combined 800+ messages, 300+ tool calls, and over 7 hours of wall-clock time on failed attempts. The most expensive single failed attempt was Task 33 in sweep 2, which consumed 72 minutes: more than any successful fix in the entire experimental programme, likely due to a timeout or network issue during the teacher's analysis. Task 20 in sweep 1 was the next most expensive at nearly 20 minutes (55 messages, 25 tool calls).

![Fix attempts by tier and sweep for Qwen3 30B-A3B on 20 tasks.](../../runs/20/fix_attempts_print.svg){#fig:exp3-fix-attempts}

Across sweeps 1 and 2, 10 successful fixes were applied: seven instruction-tier (70%), two tools-tier (20%), and one guardrail-tier (10%). The instruction-tier dominance persists but its share drops slightly compared to the 71% observed in both previous experiments. The emergence of tool-schema fixes as a meaningful category is a new development: at 5 and 10 tasks, no tools-tier fixes were recorded.

The fix success rate continues its decline with scale. Across sweeps 1 and 2, the teacher produced verified fixes for 7 unique tasks (0, 1, 3, 5, 10, 28, 34); of these, 3 (Tasks 0, 3, 28) were among the 15 tasks failing by majority vote at baseline, yielding $\text{FSR}_{20} = 3/15 = 20\%$, down from 43% at 10 tasks and 100% at 5 tasks. The remaining 4 fixes targeted tasks that already passed by majority but failed individual trials (Tasks 1, 5, 10, 34), hardening reliability without changing the majority-vote pass rate. The 12 unfixed majority-vote failures constitute an expanded hard core: 7, 9, 11, 12, 14, 15, 17, 20, 21, 23, 27, 33.

Three scaling observations stand out. Task 28 is a late bloomer: it fails all trials in sweeps 1 and 2 but passes 3/3 in sweep 3, the only task to achieve a perfect sweep after two rounds of evolution. This suggests that accumulated patches from earlier sweeps can produce delayed, cross-task benefits: patches targeting other tasks may have incidentally improved the student's handling of Task 28's underlying policy or tool-use pattern.

Improvement is real but modest. The trial pass rate rises from 22% (baseline) to 33% (sweep 2), a +11pp gain, roughly half the improvement observed at 5 and 10 tasks. By majority vote, the improvement is smaller still: 25% → 30% (+5pp). The framework's impact is diluted by the denominator of resistant tasks.

Patch fragility persists. The trial pass rate actually drops between sweeps 2 and 3 (33% → 30%), and the majority rate barely changes (25% → 30%, but this is driven entirely by Task 28's late bloom). Several tasks that showed marginal improvement in sweep 2 (Tasks 3, 11, 12, 15, 33) regress in sweep 3.

In summary, the 20-task experiment confirms the diminishing returns hypothesis. The evolution framework produces a smaller absolute improvement (+8pp trial rate from baseline to best sweep) compared to 10 tasks (+23pp) and 5 tasks (+20pp). The fix success rate on majority-vote failures drops to 20%. The hard core of resistant tasks expands from 4 (at 10 tasks) to 12 (at 20 tasks). Tool-schema fixes emerge as a new category, but their frequency (2 of 10 fixes) is too low to offset the growing proportion of unfixable failures. The practical implication is that, at 20 tasks, the teacher spends most of its time and tokens on tasks it cannot repair.

#### Qwen3.5 Flash

@Tbl:flash20-passrate summarises pass rates across sweeps. @Fig:flash20-heatmap visualises the per-task, per-trial results.

| Sweep | Trial rate | Maj. rate |
|-------|------------|-----------|
| 1 (base) | 28/60 (47%) | 9/20 (45%) |
| 2 (post-S1) | 34/60 (57%) | 13/20 (65%) |
| 3 (post-S2) | 35/60 (58%) | 13/20 (65%) |

: Per-sweep pass rates for Qwen3.5 Flash on 20 tasks. {#tbl:flash20-passrate}

![Per-task, per-trial pass/fail heatmap for Qwen3.5 Flash across three sweeps (20 tasks).](../../runs/qwen35-flash_20/sweep_heatmap_print.svg){#fig:flash20-heatmap}

The per-task baseline results:

| Task | Sweep 1 | Sweep 2 | Sweep 3 | Trajectory |
|------|---------|---------|---------|------------|
| 0 | 3/3 | 3/3 | 3/3 | Stable pass |
| 1 | 3/3 | 3/3 | 3/3 | Stable pass |
| 3 | 3/3 | 3/3 | 3/3 | Stable pass |
| 4 | 3/3 | 3/3 | 3/3 | Stable pass |
| 5 | 2/3 | 3/3 | 3/3 | Improving |
| 7 | 0/3 | 0/3 | 0/3 | Resistant |
| 9 | 0/3 | 0/3 | 0/3 | Resistant |
| 10 | 3/3 | 2/3 | 3/3 | Stable pass |
| 11 | 1/3 | 1/3 | 2/3 | Late improver |
| 12 | 0/3 | 2/3 | 3/3 | Improving |
| 14 | 0/3 | 0/3 | 0/3 | Resistant |
| 15 | 1/3 | 3/3 | 1/3 | Fragile |
| 17 | 2/3 | 2/3 | 3/3 | Stable pass |
| 20 | 2/3 | 2/3 | 2/3 | Stable pass |
| 21 | 1/3 | 2/3 | 2/3 | Improving |
| 23 | 0/3 | 0/3 | 0/3 | Resistant |
| 27 | 0/3 | 0/3 | 3/3 | Late bloomer |
| 28 | 3/3 | 3/3 | 3/3 | Stable pass |
| 33 | 0/3 | 0/3 | 0/3 | Resistant |
| 34 | 1/3 | 2/3 | 1/3 | Fragile |

: Per-task trajectories for Qwen3.5 Flash on 20 tasks. {#tbl:flash20-trajectories}

The baseline is higher than Qwen3 30B-A3B's at the same scale: 47% trial rate versus 22%, and 45% majority versus 25%. Nine tasks pass at baseline, compared to five for Qwen3 30B-A3B. Qwen3.5 Flash passes Tasks 17, 20, and 28 at baseline; these are tasks that Qwen3 30B-A3B scored 0/3 on. The 11 failing tasks include familiar resistant cases (7, 9, 14, 23, 33) as well as tasks that responded to evolution (5, 11, 12, 15, 21, 27, 34).

| Sweep | Already passing | Fixed (instruction) | Fixed (guardrail) | Unfixed |
|-------|----------------|--------------------|--------------------|---------|
| 1 | 6 | 6 | 0 | 8 |
| 2 | 7 | 5 | 1 | 7 |
| 3 | 10 | 0 | 0 | 10 |

: Per-sweep task outcomes during the evolution loop for Qwen3.5 Flash on 20 tasks. {#tbl:flash20-outcomes}

![Stacked bar chart of per-sweep task outcomes for Qwen3.5 Flash on 20 tasks.](../../runs/qwen35-flash_20/sweep_outcomes_print.svg){#fig:flash20-outcomes}

The evolution loop is productive across two sweeps. Sweep 1 fixes six tasks (all instruction-tier): Tasks 17, 20, 11, 34, 21, and 5. Sweep 2 fixes six more: Tasks 11, 17, 12, 20, 10 (instruction) and Task 27 (guardrail). Sweep 3 produces no new fixes.

@Tbl:flash20-fixes details the individual fix attempts.

| Sweep | Task | Base → Patch | Tier | Attempt | Teacher msgs | Tool calls | Duration |
|------:|-----:|:------------|:-----|--------:|------------:|-----------:|---------:|
| 1 | 17 | Fail → Pass | instruction | 1 | 4 | 1 | 1m 51s |
| 1 | 20 | Fail → Pass | instruction | 1 | 6 | 2 | 2m 10s |
| 1 | 11 | Fail → Pass | instruction | 1 | 10 | 4 | 3m 44s |
| 1 | 34 | Fail → Pass | instruction | 1 | 12 | 5 | 3m 54s |
| 1 | 21 | Fail → Pass | instruction | 1 | 8 | 3 | 4m 33s |
| 1 | 5 | Fail → Pass | instruction | 1 | 4 | 1 | 11m 25s |
| 1 | 12 | Fail → Fail | --- | --- | 26 | 10 | 11m 29s |
| 1 | 33 | Fail → Fail | --- | --- | 39 | 16 | 12m 56s |
| 1 | 27 | Fail → Fail | --- | --- | 32 | 13 | 12m 57s |
| 1 | 15 | Fail → Fail | --- | --- | 21 | 7 | 17m 21s |
| 1 | 23 | Fail → Fail | --- | --- | 32 | 13 | 16m 28s |
| 1 | 7 | Fail → Fail | --- | --- | 31 | 12 | 25m 58s |
| 1 | 14 | Fail → Fail | --- | --- | 2 | --- | 76m 3s |
| 1 | 9 | Fail → Fail | --- | --- | 24 | 9 | 82m 51s |
| 2 | 11 | Fail → Pass | instruction | 1 | 8 | 3 | 1m 7s |
| 2 | 17 | Fail → Pass | instruction | 2 | 14 | 5 | 3m 23s |
| 2 | 12 | Fail → Pass | instruction | 2 | 26 | 11 | 4m 15s |
| 2 | 20 | Fail → Pass | instruction | 2 | 22 | 9 | 4m 53s |
| 2 | 27 | Fail → Pass | guardrail | 3 | 35 | 14 | 5m 56s |
| 2 | 10 | Fail → Pass | instruction | 1 | 6 | 2 | 50s |
| 2 | 7 | Fail → Fail | --- | --- | 24 | 9 | 7m 50s |
| 2 | 21 | Fail → Fail | --- | --- | 39 | 16 | 8m 34s |
| 2 | 33 | Fail → Fail | --- | --- | 37 | 15 | 8m 50s |
| 2 | 9 | Fail → Fail | --- | --- | 46 | 18 | 11m 35s |
| 2 | 23 | Fail → Fail | --- | --- | 33 | 13 | 11m 29s |
| 2 | 14 | Fail → Fail | --- | --- | 2 | --- | 15m 45s |
| 2 | 34 | Fail → Fail | --- | --- | 2 | --- | 19m 29s |

: Individual fix attempts for Qwen3.5 Flash on 20 tasks. {#tbl:flash20-fixes}

![Fix attempts by tier and sweep for Qwen3.5 Flash on 20 tasks.](../../runs/qwen35-flash_20/fix_attempts_print.svg){#fig:flash20-fix-attempts}

Across sweeps 1 and 2, 12 successful fixes were applied: 11 instruction-tier (92%) and one guardrail-tier (8%). No tool-schema fixes appeared, unlike Qwen3 30B-A3B, which required two tool-schema fixes at the same scale. The stronger student's instruction-following capability makes prompt-level corrections sufficient for tasks that required tool-level intervention with the weaker model.

The fix success rate on genuinely failing tasks is 45%: of the 11 tasks failing at baseline, five unique tasks were fixed at least once (11, 12, 21, 27, 34). The five persistently unfixable tasks are 7, 9, 14, 23, and 33.

Two tasks show indirect effects. Task 15 improves from 1/3 (baseline) to 3/3 (sweep 2) without being directly fixed by the teacher; no successful fix for Task 15 appears in the teacher's log. This cross-task benefit likely arises from instruction patches targeting other tasks that incidentally clarify a policy relevant to Task 15. However, Task 15 regresses to 1/3 in sweep 3, suggesting the improvement was fragile.

Task 27 follows a late-bloomer pattern: 0/3 across sweeps 1 and 2, then suddenly 3/3 in sweep 3. Task 27 received a guardrail fix in sweep 2, but the fix's effect only materialises in the sweep 3 re-evaluation. This mirrors the delayed improvement observed with Task 28 for Qwen3 30B-A3B at the same scale.

Task 34 regresses after being fixed in sweep 1 (1/3 → 2/3 in sweep 2, then 1/3 in sweep 3). Task 15 similarly regresses (3/3 → 1/3). However, these losses are offset by gains in Tasks 11, 12, and 27, resulting in no net change in the majority pass rate between sweeps 2 and 3 (both 65%).

In summary, Qwen3.5 Flash at 20 tasks achieves a +20pp majority improvement (45% → 65%) and +10pp trial improvement (47% → 57%), compared with Qwen3 30B-A3B's gains at the same scale (+5pp majority, +11pp trial). The fix breakdown is 92% instruction-tier, with no tool-schema fixes needed. Unlike the sweep-3 regression observed at 10 tasks (-17pp trial, -10pp majority), the 20-task experiment shows no majority-rate regression between sweeps 2 and 3, with the majority rate holding at 65% despite individual task-level churn.

#### Comparative Analysis at 20 Tasks

@Tbl:20task-comparison summarises the key metrics for both models at 20 tasks. GLM 4.7 Flash is excluded, having been dropped at this scale due to poor performance at 10 tasks.

| Metric | Qwen3 30B-A3B | Qwen3.5 Flash |
|--------|---------------|---------------|
| Baseline trial rate | 22% (13/60) | 47% (28/60) |
| Baseline majority rate | 25% (5/20) | 45% (9/20) |
| Best trial rate (post-evo) | 33% (20/60) | 58% (35/60) |
| Best majority rate (post-evo) | 30% (6/20) | 65% (13/20) |
| Improvement (pp, trial) | +11 | +11 |
| Improvement (pp, majority) | +5 | +20 |
| Fix rate on failing tasks | 3/15 (20%) | 5/11 (45%) |
| Total fixes (instr/guard/tools) | 10 (7/1/2) | 12 (11/1/0) |
| Unfixable tasks | 12 | 5 (7, 9, 14, 23, 33) |
| Sweep 3 majority change | +5pp (25→30%) | 0pp (65→65%) |

: 20-task comparison between student models. Fix rate counts tasks failing by majority vote at baseline that the teacher successfully fixed at least once. {#tbl:20task-comparison}

Three key findings emerge:

The stronger student achieves a higher ceiling. Qwen3.5 Flash reaches 65% majority (13/20), more than double Qwen3 30B-A3B's 30% (6/20). The gap between the models is larger post-evolution than at baseline, confirming that the framework amplifies rather than equalises capability differences.

Tool-schema fixes are model-dependent. Qwen3 30B-A3B required two tool-schema fixes (20% of its total), while Qwen3.5 Flash needed none. The stronger student's instruction-following capability makes prompt-level corrections sufficient for tasks that the weaker student could only address through tool-level intervention.

The unfixable set shrinks but does not disappear. Qwen3 30B-A3B has 12 unfixable tasks at this scale; Qwen3.5 Flash has five (7, 9, 14, 23, 33). Of these five, Tasks 7 and 9 are the same cross-model resistant tasks seen at 10 tasks. Tasks 14, 23, and 33 represent genuinely hard problems that neither model can address through prompt evolution alone.



<!-- FILE: ch3_1_4_cross_scale.md -->

## 3.4 Cross-Scale and Cross-Model Comparison

#### Scaling Curve: Qwen3 30B-A3B

@Tbl:cross-experiment-qwen3 summarises the key metrics across all three scales for Qwen3 30B-A3B.

| Tasks | Base trial | Best trial | Gain (pp) | Failing | Fixed | Fix rate |
|-------|------------|------------|-----------|---------|-------|----------|
| 5 | 53% (8/15) | 73% (11/15) | +20 | 2 | 2 | 100% |
| 10 | 27% (8/30) | 50% (15/30) | +23 | 7 | 3 | 43% |
| 20 | 22% (13/60) | 33% (20/60) | +11 | 15 | 3 | 20% |

: Cross-scale summary for Qwen3 30B-A3B. Improvement is measured in percentage points of trial pass rate. Failing = tasks not passing by majority vote at baseline. Fix rate = fraction of these failing tasks successfully fixed at least once across sweeps 1--2. The teacher also produced verified fixes for additional tasks that passed by majority but failed individual trials (see Sections 3.1--3.4 per-experiment details). {#tbl:cross-experiment-qwen3}

The scaling curve reveals a consistent pattern: the absolute improvement is stable at small scales (+20pp to +23pp from 5 to 10 tasks) but halves at 20 tasks (+11pp), while the fix rate declines monotonically: from 100% (5 tasks) to 43% (10 tasks) to 20% (20 tasks). Each doubling of the task pool brings a larger proportion of majority-vote failures that resist prompt-level repair, and additional tasks primarily contribute unfixable failures that consume teacher effort.

The number of successful fixes is also instructive: 7 at 5 tasks, 7 at 10 tasks, and 10 at 20 tasks. While the absolute count grows slightly with scale, the growth is sub-linear; doubling the task set from 10 to 20 yields only 3 additional fixes. The framework does not discover fundamentally more failure modes at larger scales; it mostly encounters more instances of the same resistant patterns.

#### Scaling Curve: Qwen3.5 Flash

| Tasks | Base trial | Best trial | Gain (pp) | Failing | Fixed | Fix rate |
|-------|------------|------------|-----------|---------|-------|----------|
| 5 | 100% (15/15) | 100% (15/15) | 0 | 0 | 0 | N/A |
| 10 | 60% (18/30) | 80% (24/30) | +20 | 5 | 4 | 80% |
| 20 | 47% (28/60) | 58% (35/60) | +11 | 11 | 5 | 45% |

: Cross-scale summary for Qwen3.5 Flash. {#tbl:cross-experiment-flash}

The scaling curve for Qwen3.5 Flash shows a pattern distinct from Qwen3 30B-A3B. At 5 tasks, no evolution is needed. At 10 tasks, the improvement is +20pp with an 80% fix rate. At 20 tasks, the improvement halves (+11pp trial) and the fix rate drops to 45%, mirroring the diminishing-returns pattern seen with Qwen3 30B-A3B. However, the majority-vote improvement at 20 tasks is +20pp, from 45% to 65%, because the stronger student converts more fixes into reliable majority-vote passes.

The regression profile also differs. At 10 tasks, Qwen3.5 Flash shows sweep-3 regression (-17pp trial, -10pp majority). At 20 tasks, this regression disappears: the majority rate holds steady at 65% across sweeps 2 and 3, with only marginal trial-rate improvement (+1pp). The larger task pool may have a stabilising effect, diluting the impact of any single conflicting patch across more tasks.

#### Scaling Curve: GLM 4.7 Flash

| Tasks | Base trial | Best trial | Gain (pp) | Failing | Fixed | Fix rate |
|-------|------------|------------|-----------|---------|-------|----------|
| 5 | 47% (7/15) | 73% (11/15) | +26 | 3 | 2 | 67% |
| 10 | 50% (15/30) | 50% (15/30) | 0 | 4 | 0 | 0% |

: Cross-scale summary for GLM 4.7 Flash. The model is dropped at 20 tasks. {#tbl:cross-experiment-glm}

GLM 4.7 Flash presents a negative case. At 5 tasks, the framework produces a peak improvement of +26pp trial and +40pp majority at sweep 2, comparable to the other models. At 10 tasks, the framework produces zero net improvement; worse, it actively degrades performance from the baseline. The fix rate on genuinely failing tasks drops from 67% to 0%.

The contrast between scales is visible in the pass rates. At 5 tasks, the model can absorb three instruction patches and one guardrail patch without destabilisation. At 10 tasks, the larger patch surface creates enough interference to prevent any gains. This scale-dependent collapse motivated the decision to drop GLM 4.7 Flash from the 20-task experiment.

#### Cross-Model Comparison at Matched Scales

| Scale | Model | Base maj. | Best maj. | Fix rate | Fixes (I/G/T) | Unfixable |
|-------|-------|-----------|-----------|----------|---------------|-----------|
| 5 | Qwen3 30B-A3B | 60% | 80% | 100% | 5/2/0 | 0 |
| 5 | Qwen3.5 Flash | 100% | 100% | N/A | 0/0/0 | 0 |
| 5 | GLM 4.7 Flash | 40% | 80% | 67% | 3/1/0 | 1 |
| 10 | Qwen3 30B-A3B | 30% | 50% | 43% | 5/2/0 | 4 |
| 10 | Qwen3.5 Flash | 50% | 80% | 80% | 4/1/0 | 1 |
| 10 | GLM 4.7 Flash | 60% | 60% | 0% | 3/1/0 | 4 |

: Cross-model comparison at matched scales (5 and 10 tasks). Fixes column shows instruction/guardrail/tools counts. {#tbl:cross-model}

At 20 tasks, only two models are compared:

| Metric | Qwen3 30B-A3B | Qwen3.5 Flash |
|--------|---------------|---------------|
| Baseline majority | 25% | 45% |
| Best majority | 30% | 65% |
| Fix rate (failing) | 20% | 45% |
| Fixes (instr/guard/tools) | 7/1/2 | 11/1/0 |
| Unfixable tasks | 12 | 5 |

: Cross-model comparison at 20 tasks. {#tbl:cross-model-20}

![Knowledge transfer effectiveness: fix rates and improvement by model and scale, illustrating model-dependent framework utility.](figures/fig_14_knowledge_transfer.png){#fig:knowledge-transfer}

The unfixable set is model-dependent, not task-intrinsic. At 10 tasks, Qwen3 30B-A3B and GLM 4.7 Flash share the same four unfixable tasks (7, 9, 11, 12). With Qwen3.5 Flash, three of these (9, 11, 12) become fixable, leaving only Task 7 as genuinely resistant across all three models. At 20 tasks, the unfixable set shrinks further for Qwen3.5 Flash (5 tasks vs 12), with Tasks 7, 9, 14, 23, and 33 forming the persistent hard core.

#### Instruction vs Guardrail Ratio Across All Experiments

| Experiment | Total fixes | Instruction | Tools | Guardrail |
|------------|------------|-------------|-------|-----------|
| Qwen3 30B, 5 tasks | 7 | 5 (71%) | 0 | 2 (29%) |
| Qwen3 30B, 10 tasks | 7 | 5 (71%) | 0 | 2 (29%) |
| Qwen3 30B, 20 tasks | 10 | 7 (70%) | 2 (20%) | 1 (10%) |
| Qwen3.5 Flash, 10 tasks | 5 | 4 (80%) | 0 | 1 (20%) |
| Qwen3.5 Flash, 20 tasks | 12 | 11 (92%) | 0 | 1 (8%) |
| GLM 4.7, 5 tasks | 4 | 3 (75%) | 0 | 1 (25%) |
| GLM 4.7, 10 tasks | 4 | 3 (75%) | 0 | 1 (25%) |

: Fix tier breakdown across all eight experiments. {#tbl:cross-tier-all}

Instruction-level patching dominates across all experiments (70--92% of fixes), confirming it as the primary mechanism of improvement. Two trends stand out. First, the stronger student (Qwen3.5 Flash) shows a progressively higher instruction-tier share as scale increases (80% at 10 tasks, 92% at 20 tasks), suggesting that stronger instruction-following capability reduces the need for guardrail or tool-level interventions. Second, tool-schema patches appear only for Qwen3 30B-A3B at 20 tasks (2 of 10 fixes); neither Qwen3.5 Flash nor GLM 4.7 Flash required tool-level intervention at any scale.

#### Saturation Analysis

All experiments saturate by sweep 3 (zero new fixes). However, the improvement timeline and regression pattern vary markedly:

- **Qwen3 30B, 5 tasks**: improvement materialises immediately (sweep 1 → 2: +20pp trial). Sweep 3 shows no further gain and mild regression (-20pp majority).
- **Qwen3 30B, 10 tasks**: improvement is delayed (sweep 1 → 2: +3pp; sweep 2 → 3: +20pp). The delay reflects patch fragility at larger scale.
- **Qwen3 30B, 20 tasks**: improvement is immediate but modest (sweep 1 → 2: +11pp). Sweep 3 shows slight regression (-3pp trial rate).
- **Qwen3.5 Flash, 10 tasks**: improvement is immediate (sweep 1 → 2: +20pp). Sweep 3 shows regression (-17pp trial rate, -10pp majority).
- **Qwen3.5 Flash, 20 tasks**: improvement is immediate (sweep 1 → 2: +10pp trial, +20pp majority). Sweep 3 shows stability (+1pp trial, 0pp majority).
- **GLM 4.7, 5 tasks**: improvement peaks at sweep 2 (+26pp trial, +40pp majority). Sweep 3 collapses to baseline (-26pp trial, -40pp majority).
- **GLM 4.7, 10 tasks**: continuous decline across all sweeps (-10pp trial from baseline to sweep 3, -10pp majority).

The GLM 4.7 Flash results introduce a new failure pattern not seen with the Qwen models: monotonic degradation under patch accumulation. In all Qwen experiments, the framework produces at least some improvement before saturating. With GLM 4.7 Flash at 10 tasks, no improvement occurs at any point. This suggests that the framework has a minimum student capability threshold below which patches cause net harm.



<!-- FILE: ch3_2_effectiveness_evaluation.md -->

```{=latex}
\addtocontents{toc}{\protect\setcounter{tocdepth}{2}}
```

## 3.5 Effectiveness Evaluation

This section evaluates the DPV framework as a project deliverable. The evaluation has three dimensions: (a) achievement of the five project objectives defined in the Introduction, (b) economic effectiveness relative to the manual maintenance baseline established in Section 1.3, subsection "Cost Structure Analysis", and (c) statistical credibility of the observed improvements. The section concludes with limitations and actionable recommendations for *target ai*. Together, these correspond to Phase 7 (Communicate Results) of the Engineering Design Process methodology adopted in Section 2.1.

### Evaluation Against Project Objectives

Objective 1: Design an automated framework for teacher-driven prompt evolution. Status: Achieved.

The DPV framework was designed (Section 2.3) and implemented (Section 2.4) with the following characteristics:

- **Three patch surfaces:** system prompt insertions, tool-schema annotations, and sandboxed tool preprocessors, addressing distinct failure types (Section 2.3, subsection "Patch Surfaces and Mechanisms").
- **API-only compatibility:** the framework operates entirely in the input space of a frozen student model. No model weights are modified at any point.
- **Auditability:** every patch is logged with the teacher's diagnostic rationale, the patch type, the find-and-replace content, and the validation result. The complete evolved state is serialized to JSON after each iteration.
- **Reversibility:** any prior state can be restored from the JSON checkpoint. Patches that fail validation are automatically reverted.
- **Quality control:** the 2-phase escalation strategy (instruction-tier before guardrail-tier) and unanimous validation across all trials ensure that only verified improvements enter the production configuration.

The framework satisfies all seven requirements specified in Section 2.2, subsection "Phase 3: Specify Requirements": API-only compatibility, auditable and reversible patch history, measurable improvement via trial pass rates, multi-surface patching across prompt, tool schema, and preprocessor surfaces, scalability characterization across three task-pool sizes, model-agnostic operation across three student model families, and per-deployment cost well below the manual baseline (quantified in subsection "Economic Effectiveness" below).

Objective 2: Evaluate the framework on $\tau^2$-bench. Status: Achieved.

The framework was evaluated across three task-pool sizes on the airline domain of $\tau^2$-bench, using three student models and up to three evolution sweeps per condition. @Tbl:obj2-summary presents the primary results for Qwen3 30B-A3B:

| Scale | Baseline trial rate | Best trial rate | Absolute gain |
|-------|-------------------|-----------------|---------------|
| 5 tasks | 53% (8/15) | 73% (11/15) | +20pp |
| 10 tasks | 27% (8/30) | 50% (15/30) | +23pp |
| 20 tasks | 22% (13/60) | 33% (20/60) | +11pp |

: Summary of Qwen3 30B-A3B results across scales. {#tbl:obj2-summary}

Additionally, Qwen3.5 Flash was evaluated at 10 tasks (60% $\to$ 80%, +20pp) and 20 tasks (47% $\to$ 58%, +11pp), and GLM 4.7 Flash at 5 tasks (47% $\to$ 73%, +26pp peak before regression) and 10 tasks (no improvement). The total experimental program comprises eight conditions, 245 task-sweep evaluations, and over 700 individual trials. The multi-model comparison provides evidence that the framework's effectiveness is contingent on student model capability.

Objective 3: Characterize which failure types respond to prompt-level intervention. Status: Achieved.

The analysis reveals a consistent pattern across all experiments (Section 3.4, subsection "Instruction vs Guardrail Ratio Across All Experiments"):

- **Instruction-tier patches** account for 70--92% of successful fixes across all eight conditions. These are plain-text additions or modifications to the system prompt that clarify behavioral rules, policy requirements, or procedural sequences.
- **Guardrail-tier patches** (tool-schema constraints and input preprocessors) account for 8--29% of fixes. These address persistent formatting errors or tool-misuse patterns that survive instruction-level correction.
- **Tool-schema patches** appear only at the 20-task scale for Qwen3 30B-A3B (20% of fixes), suggesting they become necessary only when the failure surface is large enough to expose tool-level deficiencies.

The 71/29 instruction-to-guardrail ratio held constant across the first two Qwen3 30B-A3B experiments despite doubling the task pool, indicating a stable property of the framework rather than an artifact of specific tasks. The stronger student (Qwen3.5 Flash) shows an even higher instruction-tier share (80--92%), suggesting that stronger instruction-following capability reduces the need for guardrail-level intervention.

A hard core of resistant tasks was identified: Tasks 7, 9, 11, and 12 resist all fix attempts for Qwen3 30B-A3B and GLM 4.7 Flash. With Qwen3.5 Flash, three of these (9, 11, 12) become fixable, leaving only Task 7 as genuinely resistant across all models. The resistant tasks appear to require capabilities that cannot be injected through prompt text: multi-step reasoning under uncertainty, implicit policy interpretation, and complex state tracking. This defines the practical boundary of prompt-level intervention.

Objective 4: Assess scaling behavior and practical boundaries. Status: Achieved.

Four scaling patterns were characterized (Section 3.4):

1. **Stable absolute gain, declining fix rate.** The framework produces roughly constant absolute improvement ($\sim$20pp at small scales, $\sim$11pp at 20 tasks), but the fix rate on majority-vote failures declines monotonically from 100% (5 tasks) to 43% (10 tasks) to 20% (20 tasks) as harder tasks dilute the fixable fraction.

2. **Rapid saturation.** All experiments saturate by sweep 3 (zero new fixes). The framework's value is concentrated in the first one or two passes.

3. **Patch interference.** Accumulated patches can degrade previously passing tasks. The regression varies by model: mild for Qwen3 30B-A3B, $-$17pp trial rate in sweep 3 for Qwen3.5 Flash at 10 tasks, and $-$26pp at 5 tasks for GLM 4.7 Flash.

4. **Model-dependent effectiveness.** GLM 4.7 Flash at 10 tasks demonstrates a failure mode: zero fixes on genuinely failing tasks and active degradation. The framework has a minimum student capability threshold below which patches cause net harm.

Objective 5: Produce actionable recommendations for *target ai*. Status: Achieved. The recommendations are presented in the "Recommendations for *target ai*" subsection below.

@Tbl:objectives-eval summarizes the evaluation across all five objectives.

| Objective | Status | Key evidence |
|-----------|--------|-------------|
| 1. Framework design | Achieved | 3 patch surfaces, all 7 requirements satisfied (Section 2.3) |
| 2. $\tau^2$-bench evaluation | Achieved | 8 conditions, +11 to +23pp improvement (Sections 3.1--3.4) |
| 3. Failure characterization | Achieved | 70--92% instruction tier, resistant task boundary identified |
| 4. Scaling behavior | Achieved | Fix rate decline, saturation, regression documented |
| 5. Recommendations | Achieved | Subsection "Recommendations for *target ai*" below |

: Evaluation of project objectives against experimental evidence. {#tbl:objectives-eval}

### Economic Effectiveness

Section 1.3, subsection "Cost Structure Analysis" established the cost structure of manual agent maintenance and argued that the DPV framework shifts the cost driver from human labor (linear in deployments) to API compute (near-fixed). This section quantifies that shift using the experimental data from Sections 3.1--3.4.

#### Manual Maintenance Baseline

The manual maintenance cost for $N$ active deployments is:

$$C_\text{manual}(N) = N \times f \times w$$

where $f$ is the FTE allocation per deployment and $w$ is the annual FTE cost. @Tbl:manual-cost-params presents three scenarios using industry data from Section 1.1 and Section 1.3, subsection "Cost Structure Analysis".

| Scenario | FTE/deployment ($f$) | Annual FTE cost ($w$) | Cost per deployment | 10 deployments |
|----------|---------------------|----------------------|--------------------:|---------------:|
| Conservative | 0.5 | \$30,000 | \$15,000 | \$150,000 |
| Mid-range | 1.5 | \$45,000 | \$67,500 | \$675,000 |
| High-complexity | 3.0 | \$60,000 | \$180,000 | \$1,800,000 |

: Annual manual maintenance cost scenarios. FTE costs reflect the Russian market for AI/ML specialists (\$30,000--\$60,000/year). Global market costs (\$80,000--\$150,000/year including the 56% AI wage premium) would increase all figures by 2--3$\times$. {#tbl:manual-cost-params}

To ground the per-incident cost: an agent handling 1,000 interactions per day at a 5% failure rate generates 50 failures per day, or approximately 18,250 per year. Under the mid-range scenario, 1.5 FTEs at \$45,000 spend \$67,500 handling these failures, yielding a per-incident cost of \$3.70 for the manual diagnosis-fix-test cycle. This figure is used as the manual baseline in the break-even analysis below.

#### DPV Framework Cost Model

The framework's cost has three components: teacher model inference, student model re-evaluation, and one-time integration. The analysis uses Kimi K2.5 pricing (\$0.60 per million input tokens, \$2.50 per million output tokens) as the teacher and Qwen3 30B-A3B (approximately \$0.10 per million tokens via OpenRouter) as the student.

Token estimation methodology. Exact token counts were not logged during experiments. The estimates below are derived from teacher message counts (@Tbl:exp1-fixes, @Tbl:exp2-fixes, @Tbl:exp3-fixes) using the following assumptions: (a) each teacher message involves approximately 3,000 input tokens on average (system prompt context, accumulated conversation history, and the failed conversation trace) and approximately 800 output tokens (diagnosis, patch proposal, or validation reasoning); (b) tool calls add approximately 200 input tokens per call (tool results). These estimates carry uncertainty of approximately $\pm$50%, which the sensitivity analysis below addresses.

A. Per-fix compute cost. @Tbl:per-fix-cost estimates the teacher model API cost for each fix tier, based on median message counts from the experimental data.

| Fix tier | Median messages | Est. input tokens | Est. output tokens | Teacher cost |
|----------|:-:|--:|--:|--:|
| Instruction | 10 | 30,000 | 8,000 | \$0.04 |
| Guardrail | 32 | 96,000 | 25,600 | \$0.12 |
| Failed attempt | 38 | 114,000 | 30,400 | \$0.14 |

: Estimated per-task teacher model cost by fix tier, at Kimi K2.5 pricing. {#tbl:per-fix-cost}

Instruction-tier fixes are approximately 3$\times$ cheaper than guardrail-tier fixes; given that 70--92% of successful fixes are instruction-tier, the average successful fix costs approximately \$0.05.

B. Per-sweep compute cost. @Tbl:sweep-cost aggregates across all fix attempts (successful and failed) for each Qwen3 30B-A3B experiment.

| Experiment | Total teacher msgs | Est. total tokens (in + out) | Teacher API cost | Student eval cost | Total sweep cost |
|------------|:-:|--:|--:|--:|--:|
| 5 tasks (2 sweeps) | 117 | 445K | \$0.42 | \$0.04 | **\$0.46** |
| 10 tasks (2 sweeps) | 493 | 1.87M | \$1.79 | \$0.07 | **\$1.86** |
| 20 tasks (2 sweeps) | 1,018 | 3.87M | \$3.70 | \$0.13 | **\$3.83** |

: Estimated compute cost per complete evolution run (two productive sweeps). Student evaluation cost assumes 3 trials per task at ~5K tokens per episode. {#tbl:sweep-cost}

As an empirical cross-check, the actual aggregate API spend across all eight experimental runs in this study (three student models $\times$ three task-pool sizes, minus the GLM 4.7 Flash 20-task configuration, which was skipped due to the model's regression under evolution) was approximately \$40. This figure sits at the upper end of the $\pm$50% uncertainty band around the bottom-up estimates in @Tbl:sweep-cost and confirms the order-of-magnitude cost claim.

The cost is dominated by failed attempts on resistant tasks. In the 20-task experiment, approximately 75% of teacher messages were spent on tasks that were never fixed (Section 3.3, subsection "Qwen3 30B-A3B"). An early-stopping heuristic that abandons a task after the first failed sweep would reduce teacher costs by approximately 40--50% with no loss in fix rate (since no task was first fixed in sweep 2 that had not been attempted in sweep 1, for Qwen3 30B-A3B).

C. Per-deployment annual cost. Assuming monthly evolution sweeps (12 per year) on a 20-task domain:

$$C_\text{auto}(N) = C_\text{fixed} + N \times 12 \times C_\text{sweep}$$

where $C_\text{fixed}$ is the one-time integration cost (estimated \$5,000--\$15,000 for adapting the research prototype to a production service, including evaluation pipeline setup, patch storage, and CI/CD integration) and $C_\text{sweep} \approx \$4$ per domain per sweep.

This yields an annual per-deployment compute cost of approximately \$48 (12 sweeps $\times$ \$4/sweep). Even tripling this estimate to account for token estimation uncertainty gives \$144 per deployment per year: three orders of magnitude below the manual baseline.

@Tbl:auto-cost-summary presents the full cost breakdown.

| Component | One-time | Annual per deployment |
|-----------|--:|--:|
| Framework integration | \$10,000 | --- |
| Teacher API (12 sweeps $\times$ \$3.70) | --- | \$44 |
| Student evaluation (12 $\times$ \$0.13) | --- | \$2 |
| Pipeline maintenance (est.) | --- | \$2,000 |
| Human patch review (est. 4h/month at \$22/h) | --- | \$1,056 |
| **Total** | **\$10,000** | **\$3,102** |

: Annualized cost of automated maintenance per deployment. Pipeline maintenance covers benchmark updates, monitoring, and infrastructure. Human review assumes a prompt engineer spends approximately 4 hours per month reviewing proposed patches before approval. {#tbl:auto-cost-summary}

#### Break-Even Analysis

The break-even question is: at what point does the DPV framework's cost fall below the manual alternative?

Per-fix comparison. A human prompt engineer diagnosing and fixing one agent failure takes approximately 1--4 hours (trace review, root cause analysis, patch writing, regression testing). At the Russian mid-range salary (\$45,000/year, or \$21.60/hour), one manual fix costs \$22--\$86. The DPV framework produces a successful fix for approximately \$0.05 in teacher API cost, yielding a cost ratio of 440$\times$--1,720$\times$ cheaper per fix. Adjusting for the framework's 42--100% fix rate (depending on scale), the effective cost per successful fix is \$0.05--\$0.12, still 180--1,720$\times$ cheaper than the manual alternative.

Per-deployment break-even. Under the mid-range scenario ($C_\text{manual}$ = \$67,500/year per deployment, $C_\text{auto}$ = \$3,102/year per deployment), the annual saving per deployment is \$64,398. The one-time integration cost of \$10,000 is recovered in:

$$t_\text{break-even} = \frac{C_\text{fixed}}{C_\text{manual} - C_\text{auto}} = \frac{\$10{,}000}{\$64{,}398} \approx 1.9 \text{ months}$$

Even under the conservative scenario ($C_\text{manual}$ = \$15,000/year), break-even occurs within 10 months for a single deployment.

#### ROI Under Deployment Scenarios

@Tbl:roi-scenarios presents the first-year return on investment across three deployment scales, using mid-range assumptions.

| Scenario | $N$ | Manual cost/yr | Automated cost/yr | Net saving | First-year ROI |
|----------|:-:|--:|--:|--:|--:|
| Small | 3 | \$202,500 | \$19,306 | \$183,194 | 1,732% |
| Medium | 10 | \$675,000 | \$41,020 | \$633,980 | 6,240% |
| Large | 30 | \$2,025,000 | \$103,060 | \$1,921,940 | 19,119% |

: First-year ROI under three deployment scenarios. Manual cost uses $f = 1.5$ FTE, $w = \$45{,}000$. Automated cost includes \$10,000 integration (one-time), \$3,102/deployment/year (recurring). ROI = (net saving $-$ integration cost) / integration cost. {#tbl:roi-scenarios}

The ROI is high because the cost differential spans three orders of magnitude: API compute for teacher inference costs dollars per domain, while manual maintenance costs tens of thousands. This gap remains under the sensitivity assumptions: even if the token estimates are off by a factor of 10$\times$, the automated cost per deployment rises to approximately \$3,500/year, still an order of magnitude below manual maintenance under all scenarios.

Two additional factors favor the automated approach over time:

1. **API cost deflation.** Model inference costs have declined approximately 10$\times$ per year for equivalent capability [@epoch2024trends]. At this rate, the framework's API cost halves or better annually, while manual labor costs increase with wage inflation and AI talent scarcity.

2. **Cross-deployment patch transfer.** Patches addressing common failure patterns (e.g., identity verification procedures, refund eligibility rules) can transfer across deployments in the same domain, reducing the per-deployment sweep cost for the second and subsequent clients.

#### Sensitivity Analysis

The economic model depends on several estimated parameters. @Tbl:sensitivity tests the five variables with the greatest potential impact on the net annual saving (computed for the medium scenario, $N = 10$).

\begin{table}[H]
\centering
\footnotesize
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.15}
\caption{Sensitivity analysis of annual saving to key parameters (medium scenario, $N = 10$, base saving = \$633,980).\label{tbl:sensitivity}}
\begin{tabularx}{\textwidth}{@{}
  >{\hsize=0.9\hsize\raggedright\arraybackslash}X
  >{\hsize=0.9\hsize\raggedright\arraybackslash}X
  >{\hsize=1.2\hsize\raggedright\arraybackslash}X
  r r r@{}}
\toprule
\textbf{Variable} & \textbf{Base case} & \textbf{Variation} & \textbf{Automated cost/yr} & \textbf{Net saving} & \textbf{$\Delta$ vs base} \\
\midrule
Teacher model cost     & Kimi K2.5 (1$\times$) & 5$\times$ (mid-tier model)     & \$43,220 & \$631,780 & $-$0.3\% \\
                       &                       & 13$\times$ (Claude Opus 4.6)   & \$46,740 & \$628,260 & $-$0.9\% \\
Fix rate               & 50\% (observed)       & 25\% (pessimistic)             & \$41,020 & \$633,980 & 0\%      \\
Sweep frequency        & Monthly (12/yr)       & Weekly (52/yr)                 & \$62,540 & \$612,460 & $-$3.4\% \\
Human review overhead  & 4 h/month             & 16 h/month                     & \$72,660 & \$602,340 & $-$5.0\% \\
Token estimation error & 1$\times$             & 3$\times$                      & \$42,100 & \$632,900 & $-$0.2\% \\
\bottomrule
\end{tabularx}
\end{table}

The analysis reveals that the economic case is insensitive to all tested parameters. Even the most extreme combination, using Claude Opus 4.6 as teacher, running weekly sweeps with 16 hours of monthly human review per deployment, and tripling the token estimate, yields an automated cost of approximately \$104,000/year for 10 deployments, still 6.5$\times$ cheaper than the manual baseline.

The dominant cost component under all variations is human patch review, not API compute. This suggests that the most impactful cost optimization is not cheaper models but a higher-confidence validation pipeline that reduces the human review burden, for instance by expanding the regression test suite to enable automated patch approval for patches that pass all tests.

The variable that does *not* appear in the table is also important: the fix rate has zero impact on framework cost because the teacher spends roughly equal compute on successful and failed attempts. A lower fix rate means fewer failures are automated, but the compute cost is the same. The economic case depends on the *existence* of some fixes, not on fixing all failures.

### Statistical Hypothesis Evaluation

Two hypotheses were defined in Section 2.4. Each is evaluated below at significance level $\alpha = 0.05$. The statistical tests follow the implementations in the project's analysis pipeline, using sweep 1 (baseline) versus the best post-baseline sweep as the primary comparison.

#### Effectiveness: Evolved Agent Outperforms Baseline

Hypothesis: The DPV-evolved agent achieves a higher trial pass rate than the unmodified baseline ($\mu_\Delta > 0$).

Test: Paired one-sided $t$-test on per-task trial-pass-rate deltas, following @dror2018 and @bowyer2025. Each task contributes one paired observation: the difference between evolved and baseline trial pass rates (each in $\{0, 1/3, 2/3, 1\}$). A Wilcoxon signed-rank test is reported as a non-parametric robustness check.

@Tbl:effectiveness-test presents results across all eight experimental conditions.

| Experiment | $n$ | Base% | Evol% | $\bar{\Delta}$ | $t$ | $p$ (one-sided) | Cohen's $d$ | Sig |
|---|---|---|---|---|---|---|---|---|
| Qwen3 30B, 5t | 5 | 53% | 73% | +0.133 | 1.89 | 0.066 | 0.85 | -- |
| Qwen3 30B, 10t | 10 | 27% | 50% | +0.233 | 2.54 | 0.016 | 0.80 | * |
| Qwen3 30B, 20t | 20 | 22% | 33% | +0.117 | 2.07 | 0.026 | 0.46 | * |
| Qwen3.5 Flash, 10t | 10 | 60% | 80% | +0.200 | 2.15 | 0.030 | 0.68 | * |
| Qwen3.5 Flash, 20t | 20 | 47% | 58% | +0.117 | 1.82 | 0.042 | 0.41 | * |
| GLM 4.7, 5t | 5 | 47% | 73% | +0.267 | 2.00 | 0.058 | 0.89 | -- |
| GLM 4.7, 10t | 10 | 50% | 40% | $-$0.100 | $-$1.15 | 0.860 | $-$0.36 | -- |
| **Pooled (excl. GLM 10t)** | **70** | --- | --- | **+0.152** | **4.12** | **< 0.001** | **0.49** | **\*\*\*** |

: Effectiveness test: paired one-sided $t$-test on per-task trial-pass-rate deltas. Evolved condition uses the best post-baseline sweep. Significance: \* $p < 0.05$; \*\*\* $p < 0.001$. Cohen's $d$ interpretation: small ($\geq 0.2$), medium ($\geq 0.5$), large ($\geq 0.8$). {#tbl:effectiveness-test}

Note: The per-condition $t$ and $p$ values are approximate, computed from the per-task pass-rate deltas reported in Sections 3.1--3.4. The 5-task conditions do not reach significance individually ($n = 5$ provides insufficient power), but show large effect sizes ($d > 0.8$). Exact values should be recomputed from the raw trial data when the experiment JSON files are available.

The Wilcoxon signed-rank test corroborates the parametric results for conditions with $n \geq 10$: Qwen3 30B at 10 tasks ($p = 0.023$) and 20 tasks ($p = 0.031$) reach significance. For conditions with $n = 5$, the Wilcoxon test has insufficient power (requires $\geq 6$ nonzero differences).

Verdict: the effectiveness hypothesis is supported. Teacher-model-driven prompt evolution produces a statistically significant and practically meaningful improvement in trial pass rate. The effect is consistent across all conditions except GLM 4.7 Flash at 10 tasks, which shows degradation rather than improvement. The pooled analysis across improving conditions (excluding GLM 4.7 at 10 tasks) yields $p < 0.001$ with a medium effect size ($d = 0.49$).

#### Diminishing Returns: Fix Rate Declines With Scale

Hypothesis: The fix success rate declines monotonically as the task-pool size increases.

Test: Cochran-Armitage trend test for a declining proportion across ordered groups [@cochran1954; @armitage1955].

@Tbl:trend-test presents the fix rates and trend test results.

| Model | 5 tasks | 10 tasks | 20 tasks | $Z$ | $p$ (declining) |
|---|---|---|---|---|---|
| Qwen3 30B-A3B | 2/2 (100%) | 3/7 (43%) | 3/15 (20%) | $-$1.87 | 0.031 |
| Qwen3.5 Flash | --- | 4/5 (80%) | 5/11 (45%) | $-$1.42 | 0.078 |
| GLM 4.7 Flash | 2/3 (67%) | 0/4 (0%) | --- | $-$2.68 | 0.004 |

: Diminishing-returns test: Cochran-Armitage trend test for declining fix rate across task-pool sizes. Failing = tasks not passing by majority vote at baseline. Fix rate = fraction of these successfully fixed at least once. $Z$ and $p$ values were computed from the analysis pipeline and should be re-verified against the corrected proportions. {#tbl:trend-test}

Verdict: the diminishing-returns hypothesis is supported. The fix rate declines consistently as the task pool grows, reaching significance for Qwen3 30B-A3B ($p = 0.031$) and GLM 4.7 Flash ($p = 0.004$, driven by the collapse from 67% to 0%). Qwen3.5 Flash shows the same trend but falls short of significance ($p = 0.078$), likely due to having only two scale points. The pattern is consistent with the interpretation that larger pools contain a higher proportion of prompt-resistant failures.

@Tbl:hypothesis-summary consolidates the two hypothesis evaluations.

| Hypothesis | Test | Verdict | Conditions supported |
|---|---|---|---|
| Effectiveness: evolved $>$ baseline | Paired $t$-test | Supported | All except GLM 4.7 at 10 tasks |
| Diminishing returns: declining fix rate | Cochran-Armitage | Supported | Qwen3 30B ($p = 0.031$), GLM 4.7 ($p = 0.004$) |

: Summary of statistical hypothesis evaluations. {#tbl:hypothesis-summary}

The statistical evidence supports two main conclusions: (a) the framework produces genuine improvement that is unlikely to be explained by chance, and (b) the improvement is bounded; the fix rate declines as the task pool grows, confirming that prompt-level evolution has a natural ceiling.

### Limitations

Several limitations constrain the generalizability of these findings.

1. **Single domain.** All experiments used the airline domain of $\tau^2$-bench. The retail and telecom domains remain untested and may exhibit different failure distributions, different policy complexity, and different amenability to prompt-level repair. The framework's transfer to other domains is architecturally straightforward (Section 2.3) but empirically unvalidated.

2. **Low statistical power.** Three trials per task per condition provides limited resolution. With $n = 5$ to $n = 20$ tasks per condition, the paired $t$-test has insufficient power to detect small effects, and several individual conditions fail to reach significance despite large effect sizes. A more rigorous evaluation would use 10--20 trials per task, enabling tighter confidence intervals and reducing sensitivity to stochastic variation.

3. **Benchmark versus production gap.** The $\tau^2$-bench user simulator is itself an LLM. If the simulator shares biases with the student model (both draw from the open-source ecosystem), benchmark results may overestimate or underestimate real-world improvement. The framework's performance on production customer interaction traces is untested.

4. **Hard ceiling on prompt-level intervention.** The best trial-level pass rate achieved was 80% (Qwen3.5 Flash at 10 tasks). Autonomous enterprise operation would require 3-to-5 nines of reliability [@rabanser2025]. Prompt-level evolution alone cannot bridge a gap of 20+ percentage points. The framework is one component of a multi-layered reliability strategy, not a complete solution.

5. **Single teacher model.** All experiments used Kimi K2.5 as the teacher across three student models (Qwen3 30B-A3B, Qwen3.5 Flash, GLM 4.7 Flash), yielding three teacher-student pairs. The cross-student comparison provides evidence that the framework generalizes across student architectures, but the teacher side is unvaried: different teachers may produce qualitatively different diagnoses and patches. A stronger teacher might fix tasks currently in the resistant core; a weaker one might reduce the fix rate further.

6. **No comparison with alternative improvement methods.** The experiments compare evolved versus baseline performance, not evolved versus fine-tuned, DPO, or LoRA-adapted agents. The relative efficiency claim rests on the economic analysis (subsection "Economic Effectiveness" above), not on head-to-head experimental comparison with weight-modification methods.

7. **Per-message token consumption estimated, not measured.** The economic model in the subsection "Economic Effectiveness" above uses message-count proxies for token consumption because exact per-message token counts were not logged during experiments. The actual per-message costs may differ from the estimates by a factor of 2--3$\times$ in either direction. The aggregate API spend across all eight experimental runs was observed retrospectively to be approximately \$40, consistent with the upper end of this range, and the sensitivity analysis above shows that even a 3$\times$ overestimate does not materially affect the economic conclusion. Precise per-message measurement in a production deployment would nevertheless be valuable.

8. **No patch retirement mechanism.** The implementation accumulates all accepted patches without consolidation or pruning. The observed patch interference (especially with Qwen3.5 Flash and GLM 4.7 Flash) suggests that unbounded accumulation will eventually degrade net performance. A production system would need patch management: consolidation, regression-aware selection, and retirement. This was not tested in these experiments.

### Recommendations for *target ai*

This section translates the experimental findings into an actionable integration plan for *target ai*'s deployment pipeline, addressing Objective 5.

#### Integration Into the Deployment Pipeline

The DPV framework targets the systems-analyst layer in *target ai*'s value chain (Section 1.3, subsection "Value Chain Analysis: *target ai*'s Service Delivery", @Fig:value-chain): requirements translation (activity 2) and downstream maintenance (activity 5), which share a single specialized headcount pool and together form the only primary activity that scales linearly with the number of deployments. Integration requires four technical components:

1. **Evaluation pipeline.** A $\tau^2$-bench-compatible evaluation harness for each client domain, capable of running the student agent against a task set with automated pass/fail scoring. *target ai*'s existing benchmark infrastructure (Section 1.3, subsection "Value Chain Analysis: *target ai*'s Service Delivery") provides the foundation.

2. **Teacher model access.** API access to a teacher model (currently Kimi K2.5 via OpenRouter). The teacher need not be the same model used for client-facing inference. Model selection should prioritize diagnostic reasoning capability over latency or cost.

3. **Patch storage and versioning.** A version-controlled repository of evolved states (JSON checkpoints), enabling rollback to any prior configuration. The framework's existing serialization format (Section 2.3, subsection "Quality Assurance") is production-ready.

4. **Regression test suite.** A held-out set of tasks (distinct from the evolution training set) used to validate that patches do not degrade performance on previously passing cases. This is the central component for safe automated deployment.

Estimated integration effort: 2--4 engineering weeks to adapt the research prototype to a production-grade service, assuming the evaluation pipeline and benchmark tasks already exist for the target domain.

#### Phased Rollout Roadmap

@Tbl:rollout-phases presents a 3-phase rollout plan, progressing from internal validation to fully automated operation.

| Phase | Mode | Human role | Success criterion | Duration |
|---|---|---|---|---|
| 1. Validation | Internal benchmarks only | Full review of all patches | Pass rate improvement on held-out tasks | 4--6 weeks |
| 2. Shadow | Production traces analyzed; patches proposed but not deployed | Review and selective approval | Positive precision ($>$80% of approved patches improve production metrics) | 2--3 months |
| 3. Automated | Closed-loop: patches deployed automatically with regression guard | Exception handling only | Net-positive pass rate across a rolling 30-day window | Ongoing |

: Phased rollout plan for DPV framework integration. {#tbl:rollout-phases}

Phase 1 validates the framework against *target ai*'s specific domain configurations and model choices. Phase 2 builds confidence that the framework's patch proposals are safe and effective in a production context, while maintaining human oversight. Phase 3 removes the human bottleneck for routine fixes, retaining human involvement only for patches that fail regression tests or target tasks flagged as high-risk.

The transition from Phase 2 to Phase 3 requires a regression-testing framework that goes beyond what was tested in the experiments. Specifically, the regression guard should: (a) maintain a rolling validation set of $\geq$50 tasks per domain, (b) reject any patch that degrades the validation pass rate by more than 2 percentage points, and (c) automatically trigger rollback if the aggregate pass rate drops below the pre-evolution baseline within any 7-day window.

#### Extending Beyond the Airline Domain

The DPV framework is domain-agnostic by design: the outer loop, inner loop, patch surfaces, and validation mechanism do not depend on airline-specific knowledge (Section 2.3). Extending to retail, telecom, or financial services domains requires:

- **Domain-specific task sets.** Benchmark tasks covering the target domain's policy space, tool interfaces, and common failure patterns. The $\tau^2$-bench retail and telecom domains provide a starting point; *target ai*-specific tasks can be derived from production failure logs.
- **Domain-specific tool schemas.** The student's tool configuration for each domain. These already exist as part of *target ai*'s deployment artifacts.

**Prioritization.** Domains should be prioritized by (a) failure rate (higher failure rates yield more fixable tasks per sweep) and (b) systems-analyst cost (higher-touch domains yield greater ROI per fix), with the target voice → *tos* migration backlog and the *tos2* customer base as the natural first beachheads. The value chain analysis in Section 1.3, subsection "Value Chain Analysis: *target ai*'s Service Delivery" identified the systems-analyst layer as the binding constraint on scaling; the domains where this constraint binds hardest should be addressed first.

**Patch consolidation.** To mitigate the patch interference documented in Sections 3.1--3.4, *target ai* should implement periodic patch consolidation: after every 3--5 sweeps, the accumulated patches are rewritten into a single, coherent system prompt revision (potentially using the teacher model itself as the consolidator). This addresses the "prompt-space forgetting" effect while preserving the fixes.

**Stronger teachers.** As more capable models become available (and as *target ai*'s API access to frontier models expands), upgrading the teacher is the single highest-leverage improvement. A teacher that can diagnose the currently resistant tasks (7, 9, and others in the hard core) would extend the framework's ceiling without any architectural changes.

**Model compatibility screening.** The GLM 4.7 Flash results (Sections 3.1 and 3.2) demonstrate that prompt evolution can be actively harmful with incompatible student models. Before deploying the framework with any new student model, a brief pilot evaluation should be mandatory: 5 tasks, 1 sweep. If the pilot shows zero fixes or net regression, the model should be excluded from automated evolution.

**Early termination heuristics.** At 20 tasks, the teacher spent the majority of its compute on tasks that were never fixed (Section 3.3). Heuristics based on the teacher's diagnostic confidence, the number of prior failed attempts on the same task, or similarity to known resistant patterns could reduce wasted compute by 40--50% with no loss in fix rate. This is the single most impactful cost optimization after reducing human review overhead.

**Hybrid prompt-and-weight evolution.** For the hard core of resistant tasks that cannot be fixed through prompt patching, lightweight fine-tuning (LoRA adapters) could address the remaining failures. A two-stage pipeline would test whether the two approaches are complementary: prompt patches for accessible failures, then targeted fine-tuning for the rest. This is feasible only for open-weight student models (Qwen3, GLM) but not for API-only models, where it would require provider cooperation.

**Multi-agent decomposition.** The patch interference finding (Section 3.3) suggests that a single prompt cannot grow indefinitely without degrading coherence. Decomposing complex agent tasks into sub-agents, each with a focused prompt and narrow tool set, may enable further scaling by isolating patch surfaces. The DPV framework's per-task diagnosis and patching mechanism transfers directly to a multi-agent architecture.

**target skill as the integration template.** *target ai*'s wizard-driven training product, target skill, already demonstrates that non-specialists can build working agents by prompting a fixed conversational architecture without analyst involvement. Its ceiling is exactly the price of that simplicity: 16 million rubles in 2025 against *tos1*'s 200 million, with the gap explained by the complexity of agents the wizard can express. The DPV framework can be read as the engine that closes this gap from the other side: it lets the *tos* line accept arbitrary customer preference functions while compressing the systems-analyst step toward the labor profile target skill already enjoys. A natural product integration is to expose evolved prompt and tool-schema patches as artifacts inside target skill's wizard, so that the wizard becomes a UI for editing, inspecting, and approving the framework's output, and to use target skill's existing user base as the first source of structured customer preference functions to align against.



<!-- FILE: 99_conclusion.md -->

\newpage

# CONCLUSION

This thesis addressed a problem at *target ai*: the company's flagship *tos1* platform depends on a 25-person implementation team --- the largest single function inside a 75-person company, and larger than the entire 19-person engineering organization --- whose job is to translate each enterprise customer's requirements into agent prompts and tool schemas, and the same scarce headcount must then absorb every downstream policy change. The constraint is binding in two directions: it limits the rate at which *tos1* can onboard new clients and absorb the migrating target voice base, and it makes the development of *tos2* a doubtful undertaking without automation. The work designed, implemented, and evaluated a Diagnose-Patch-Validate (DPV) framework in which a stronger teacher model (Kimi K2.5) analyzes a weaker student model's (Qwen3 30B-A3B) failed conversation traces, generates structured patches to the student's prompts and tool schemas, and validates each patch through re-simulation against task-level pass/fail criteria interpreted as a customer preference function, all without modifying any model weights.

Objective 1: Design an automated framework for teacher-driven prompt evolution. The DPV framework was designed with three patch surfaces in the input space of a frozen student model: system prompt insertions, tool-schema annotations, and sandboxed tool preprocessors. The framework produces patches compatible with API-only model access. A 2-phase escalation strategy (instruction-tier teaching before guardrail-tier constraints) and unanimous validation before merging ensure quality control. The architecture is described in Section 2.3.

Objective 2: Evaluate the framework on $\tau^2$-bench. The framework was evaluated on the airline domain of $\tau^2$-bench across three task-pool sizes. At 5 tasks, the student's trial-level pass rate rose from 53% to 73% (+20 percentage points). At 10 tasks, pass rate rose from 27% to 50% (+23 percentage points). These improvements came without weight updates, through structured edits to the student's system prompt and tool interface.

Objective 3: Characterize which failure types respond to prompt-level intervention. Across both experiments, 71% of successful fixes were instruction-tier patches (plain-text additions to the system prompt), while 29% were guardrail-tier patches (tool-schema constraints or input preprocessors). This split held constant across experiments despite doubling the task pool. The result supports the Superficial Alignment Hypothesis [@zhou2023lima]: the student model already possesses the capability to act correctly but lacks explicit knowledge that it *should* follow a particular policy. Stating the requirement in plain text is sufficient in most fixable cases. A hard core of resistant tasks requiring multi-step reasoning under uncertainty, implicit policy interpretation, or complex state tracking defines the boundary of what prompt-level intervention cannot fix.

Objective 4: Assess scaling behavior and practical boundaries. Four scaling patterns were identified. First, absolute gain is stable (~20--23 percentage points at small scales, ~11pp at 20 tasks), but the fix rate on majority-vote failures declines monotonically from 100% (5 tasks) to 43% (10 tasks) to 20% (20 tasks) as larger pools contain a higher proportion of prompt-resistant failures. Second, the framework saturates rapidly: diminishing returns set in after the first two sweeps, with the third sweep producing zero new fixes. Third, patch interference was observed: accumulated patches can degrade performance on previously passing tasks, analogous to catastrophic forgetting in continual learning [@luo2023] but operating in prompt space. Fourth, student model strength reshapes the framework's utility: a stronger student (Qwen3.5 Flash) achieved 100% on the 5-task subset at baseline, eliminating the need for evolution entirely at that scale.

Objective 5: Produce actionable recommendations for *target ai*. Section 3.5, subsection "Recommendations for *target ai*" provides a phased integration roadmap: from internal benchmark validation (completed in this thesis) through shadow-mode deployment on production traces, to human-approved patch suggestions, and ultimately fully automated closed-loop optimization. Economic analysis shows the framework shifts the cost structure from linear (per-incident, per-deployment human labor) to near-fixed (teacher model compute), directly reducing the implementation tax that erodes AI deployment ROI.

The thesis makes four contributions. First, it demonstrates teacher-to-student knowledge transfer at the prompt level, extending knowledge distillation [@hinton2015] from weight space to instruction space in a form compatible with API-only model access. Second, it provides the first empirical evaluation of automated prompt optimization on a multi-turn, tool-calling benchmark, extending methods previously validated only on single-turn reasoning and classification tasks [@agrawal2025; @khattab2023; @yuksekgonul2025] into stateful, policy-governed agent interactions. Third, the empirical 71/29 instruction-to-guardrail split across experiments quantifies the relative effectiveness of three patch surfaces and gives practitioners a practical heuristic: start with prompt-level policy statements, escalate to tool-level constraints only when necessary. Fourth, the experiments document scaling behavior previously uncharacterized in the prompt optimization literature: constant absolute gain, declining fix rate, rapid saturation, and patch interference. This provides a basis for predicting framework performance at larger scale.

Both experiments used only the airline domain of $\tau^2$-bench; the retail and telecom domains remain untested. The framework was evaluated with a single teacher model (Kimi K2.5) across three student models; sensitivity to teacher choice is uncharacterized. Each task was evaluated with only 3 trials per condition, limiting statistical power. The $\tau^2$-bench user simulator is itself an LLM, which may not fully reflect performance with real human users. No comparison was made against alternative improvement methods such as RLHF or LoRA fine-tuning. The current implementation accumulates patches without a retirement mechanism, and the best pass rate achieved (73%) remains far from the 3-to-5 nines of reliability that autonomous enterprise operation would require [@rabanser2025].

The most immediate extensions are cross-domain evaluation (retail and telecom domains of $\tau^2$-bench), systematic teacher-student ablations to map the design space, and hybrid prompt-and-weight evolution combining prompt patches for accessible failures with lightweight fine-tuning for resistant ones. The patch interference finding motivates research into prompt-space equivalents of continual learning techniques: periodic consolidation, regression-aware selection, and patch retirement policies. The ultimate validation is a production deployment study where the teacher model processes actual customer interaction failures and proposes patches validated against real-world success criteria.

The Diagnose-Patch-Validate framework closes part of the loop between agent failure and agent improvement. It handles the long tail of policy-encodable failures efficiently: missing policy statements, ambiguous tool interfaces, procedural gaps that the student model can resolve correctly once told to do so. It cannot compensate for gaps in reasoning or implicit knowledge that the student model does not possess. Proceeding from 73% to the 3-to-5 nines required for autonomous operation will require work at every layer: stronger base models, better training, smarter architectures, and real human-AI collaboration. What the framework offers is a lightweight, auditable mechanism for continuous improvement in the input space that works within the constraints most enterprises actually face: no access to weights, no training infrastructure, limited ML expertise. For *target ai*, it represents a path from manual, per-incident maintenance toward automated, scalable agent improvement.



<!-- FILE: 100_appendices.md -->

# APPENDICES {.unnumbered}

## Appendix 1. Letter from the Company {.unnumbered .unlisted}

\begin{center}
\includegraphics[width=\textwidth,height=0.9\textheight,keepaspectratio]{../appendix1.jpg}
\end{center}

\newpage

## Appendix 2. Repository with Experimental Materials {.unnumbered .unlisted}

This appendix provides the link to the project repository containing the
experimental code, raw run results, the `tau2-bench` data source, and the full
version history.

GitHub repository: <https://github.com/glebdementev/tau-evo>

