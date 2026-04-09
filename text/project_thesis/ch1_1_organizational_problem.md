# 1.1 The Organizational Problem

This section introduces the organization at the center of this project, defines the operational problem that motivates the work, and establishes the study's scope and objectives.

## 1.1.1 TargetAI LLC: Company Profile

TargetAI LLC is a Russian technology company operating in the customer experience (CX) automation market. The company develops and deploys AI-powered solutions for enterprise clients across retail, telecom, airline, and financial services verticals. Its product portfolio includes three core offerings:

- **TargetAI Platform** --- an omnichannel automation platform that orchestrates AI agents across voice, chat, and messaging channels, enabling enterprises to automate customer interactions at scale.
- **TargetSpeak** --- a voice AI product that handles inbound and outbound calls using natural language understanding and generation, integrated with telephony infrastructure and CRM systems.
- **TargetSkill** --- an agent training and quality assurance tool that analyzes conversation logs, identifies performance gaps, and generates training materials for both human and AI agents.

TargetAI serves enterprise clients who require high-reliability customer service automation. The company's agents are deployed via API-served models---primarily through OpenRouter and direct provider APIs---meaning TargetAI has no access to model weights and cannot employ fine-tuning or reinforcement learning from human feedback (RLHF) to correct agent behavior.

## 1.1.2 The Problem: Static Agents in a Dynamic Environment

The core operational problem is that deployed AI agents are static: once their prompt and tool configuration are set, they do not learn from the failures that follow. A static agent that fails on a policy edge case on Monday will fail on the same edge case on Tuesday, and on every subsequent encounter, unless a human engineer manually diagnoses the failure, rewrites the prompt or tool schema, and re-deploys the agent.

At enterprise scale, where thousands of edge cases accumulate across dozens of policy domains, this manual remediation loop becomes the primary operational bottleneck. Every policy change, product update, or regulatory shift requires a human expert to revisit and re-engineer the agent's prompts and tool schemas. The problem is compounded by *agent drift*: LLM agents exhibit progressive behavioral degradation over extended deployment even without explicit parameter changes, as input distributions shift and accumulated context alters model behavior [@agentdrift2025]. @informatica2025 quantify the scope: 91% of AI models experience quality degradation over time, requiring continuous re-optimization rather than one-time configuration.

## 1.1.3 Quantified Impact

The implementation tax imposed by manual agent maintenance is substantial:

- **Labor cost:** Post-deployment maintenance requires 0.5 to 3 full-time equivalents and \$50,000--\$100,000 per year per deployment [@gartner2025complexity]. Enterprise implementations routinely cost three to five times the initially advertised price once integration and maintenance are included [@acceldata2025].
- **Talent scarcity:** Workers with AI skills command a 56% wage premium, up from 25% in 2024 [@pwc2025aijobs]. Prompt engineers earn a median of \$126,000--\$128,000, with senior roles reaching \$300,000+ [@glassdoor2025prompt]. Over 90% of global enterprises will face critical AI skills shortages by 2026 [@idc2025skills].
- **Services overhead:** Professional services account for 60--70% of total project cost versus only 30--40% for platform licensing [@opexengine2024]. AI-first companies operate at 50--60% gross margins, well below the 75--90% typical of traditional SaaS [@bessemer2025].
- **Failure rate:** Over 80% of AI projects fail to reach production [@ryseff2024], and 95% of generative AI pilots fail to deliver measurable P\&L impact [@mitnanda2025]. Only 25% of enterprises have moved more than 40% of their AI pilots into production [@deloitte2026ai]. Forrester estimates that three out of four firms attempting to build agentic architectures independently will fail [@forrester2025].

For TargetAI specifically, each deployed client engagement requires dedicated prompt engineering effort that scales linearly with the number of domains and policy updates. As the client base grows, the maintenance burden grows proportionally, constraining the company's ability to scale profitably.

## 1.1.4 The Constraint: API-Only Model Access

TargetAI's operational model imposes a critical technical constraint: all models are consumed through APIs without access to model weights. This rules out fine-tuning, RLHF, DPO, and any other weight-modification approach to improving agent behavior. The constraint is not unique to TargetAI---it reflects the dominant access pattern for enterprises that lack ML infrastructure, as frontier capabilities concentrate in a handful of providers. The constraint is further reinforced by sanctions-driven limitations on access to Western frontier models (GPT-4, Claude) in Russia, making model-agnostic, API-compatible solutions especially relevant.

## 1.1.5 Object, Subject, and Scope

**Object of study:** TargetAI's CX automation platform and the AI agents deployed through it.

**Subject of study:** the process of post-deployment improvement of API-served AI agents through automated prompt and tool-schema evolution.

**Scope:** The study is limited to the airline domain of the $\tau^2$-bench benchmark [@barres2025] as a proxy for TargetAI's operational domains. It evaluates three student models (Qwen3 30B-A3B, Qwen3.5 Flash, GLM 4.7 Flash) with a single teacher model (Kimi K2.5) across task-pool sizes of 5, 10, and 20 tasks. The framework operates entirely in the input space of the student model---no model weights are modified.

## 1.1.6 Project Objectives

To address the organizational problem, this thesis pursues five project objectives:

1. **Design an automated framework for teacher-driven prompt evolution.** Architect a diagnose-patch-validate loop with three patch surfaces---system prompt insertions, tool-schema edits, and sandboxed tool preprocessors---that operates entirely in the input space of a frozen student model and produces auditable, versionable, rollback-able changes compatible with API-only model access.

2. **Evaluate the framework on $\tau^2$-bench as a proxy for TargetAI's operational domains.** Run baseline and post-evolution evaluations of a small open-source student model (Qwen3 30B-A3B) on the $\tau^2$-bench airline domain across increasing task-pool sizes (5, 10, and 20 tasks) to measure effectiveness under controlled conditions.

3. **Characterize which failure types respond to prompt-level intervention.** Analyze the distribution of successful and unsuccessful patches across the failure taxonomy (tool misuse, policy violation, reasoning error, communication error) to identify the boundaries of what prompt-level evolution can and cannot fix.

4. **Assess scaling behavior and practical boundaries.** Determine whether the fix rate holds as the task pool grows or degrades, establishing the practical limits of the approach and identifying where complementary methods (e.g., fine-tuning, architectural changes) would be needed.

5. **Produce actionable recommendations for TargetAI's deployment pipeline.** Translate experimental findings into a phased integration roadmap---from internal benchmark validation through shadow-mode deployment to fully automated closed-loop optimization---with defined team responsibilities, cost projections, and success criteria.

## 1.1.7 Relevance

The problem addressed by this thesis is relevant at three levels:

- **Business relevance:** The "Services as Software" market is estimated at \$4.6 trillion [@foundationcapital2024]. McKinsey projects that agentic AI could unlock \$100--400 billion in incremental spending in tech services alone by decade's end [@mckinsey2025techservices]. Reducing the implementation tax is a prerequisite for capturing this opportunity.

- **Industry relevance:** The shift to outcome-based pricing---where vendors bear the economic risk of agent performance directly---transforms agent reliability from a quality concern into a direct margin driver. Intercom charges \$0.99 per resolution [@intercom2024]; Sierra implements pure outcome-based pricing [@sierra2024]. Under these models, every unresolved interaction is revenue forgone. Automated maintenance is a competitive differentiator.

- **Organizational relevance:** For TargetAI, the framework directly addresses the highest-cost, lowest-automation activity in its service delivery chain. By converting failure diagnosis from a per-incident human task to an automated process, the framework shifts the cost structure from linear (proportional to failure volume and deployment count) to near-fixed (the compute cost of running the teacher model).
