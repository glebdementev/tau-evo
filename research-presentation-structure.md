# Research Presentation Structure Template

A reusable framework extracted from an academic thesis defense on "Applying LLMs to Dialogue Communication Analytics." This structure builds a persuasive research argument in a logical sequence that works for any empirical or applied research topic.

---

## How Your Presentation Built Its Argument

Your deck followed a tight **Context → Gap → Goal → Method → Evidence → Verdict** arc across 18 slides. Here's a translation of each section and what it accomplished rhetorically:

### 1. Title Slide
**Your slide:** "Applying Large Language Models to Dialogue Communication Analytics" — author, supervisor, date.
**Purpose:** Anchor the audience: who you are, what this is about, when.

### 2. Terminology (1 slide)
**Your slide:** Defined "Speech Analytics" and "Large Language Models" side by side.
**Purpose:** Level-set the audience so nobody gets lost in jargon. By placing both terms together, you implied a connection before explicitly stating one.

### 3. Relevance / Why This Matters (1 slide)
**Your slide:** A 2x2 matrix — problems of speech analytics, value of LLMs, value of speech analytics, problems of LLMs — with a central intersection "LLMs in speech analytics."
**Purpose:** This is the tension slide. You showed that speech analytics has real value but is stalling (15% CAGR vs. 24% for Conversational AI overall), and LLMs are powerful but poorly understood. The implicit argument: combining them could unlock something, but nobody has tested it properly.

### 4. Problem & Goal (1 slide)
**Your slide:** One-line problem statement, one-line goal, then a two-column table mapping 5 research tasks to their expected deliverables.
**Purpose:** Converts the tension into a concrete research agenda. The tasks-to-deliverables table signals rigor — you're not exploring vaguely, you have a plan with checkpoints.

### 5. Theoretical Framework (1 slide)
**Your slide:** Two-column summary — Speech Analytics (market size, how it works, its limitations) vs. LLMs (architecture, capabilities, limitations).
**Purpose:** Compressed literature review. Establishes credibility by showing you know the field, while keeping it digestible.

### 6. Dataset (1 slide)
**Your slide:** 459 dialogues across 4 business domains (medical clinic, car dealership, beverage retail, pharmacy), with distribution charts and a domain table.
**Purpose:** Makes the study tangible. The audience now knows the scale, variety, and source of the data. The 4-domain spread preemptively addresses "but does it generalize?"

### 7. Model Selection (1 slide)
**Your slide:** Selection criteria (context length, parameter count, API access, cost), resulting in 5 models: Llama 3 70B, GigaChat Pro, YandexGPT Pro, GPT-3.5 Turbo, Claude 3 Haiku.
**Purpose:** Demonstrates methodological rigor. You didn't just pick favorites — you applied filters and justified each choice.

### 8. Question Formation / Experiment Design (1 slide)
**Your slide:** Table of 6 task types (problem identification, commonsense reasoning, sentiment analysis, semantic extraction, NER, entity extraction) with examples, plus explanation of manual ground-truth labeling and 3x repetition at temperature 0.1.
**Purpose:** The "how" slide. Converts the abstract goal into a concrete, reproducible experiment. The 3x repetition and low temperature show statistical discipline.

### 9. Evaluation Method (1 slide)
**Your slide:** Flowchart showing how LLM answers were compared to ground truth — string matching for closed questions, GPT-4 as semantic judge for open questions.
**Purpose:** Addresses the hardest methodological question: "how do you score open-ended answers?" Using GPT-4 as an arbiter (citing precedent in literature) is a creative solution, and the flowchart makes it transparent.

### 10-14. Results (5 slides, one finding per slide)
Each slide presented one hypothesis test with supporting visualization:
1. **Model ranking** — Haiku best overall, GPT-3.5 not statistically worse (violin plot)
2. **Accuracy thresholds** — top models achieve 70%/80%+ accuracy zero-shot (heatmap matrix)
3. **Domain dependence** — quality varies across business domains, from minor to significant (bootstrap distributions)
4. **Task dependence** — task type matters 3x more than model choice; commonsense reasoning at 95% accuracy, NER hardest (ranked matrix)
5. **Length independence** — dialogue length doesn't predict answer quality (scatter plots, Hoeffding test)

**Purpose:** Each slide = one claim + one proof. This drip-feed approach lets the audience absorb findings incrementally instead of drowning in a data dump.

### 15. Hypothesis Summary (1 slide)
**Your slide:** Table of all 5 hypotheses with results and checkmark/X icons.
**Purpose:** The verdict slide. After 5 detail slides, you pull back and give a scoreboard. 3 confirmed, 2 partially rejected — this honesty strengthens credibility.

### 16. Conclusion (1 slide)
**Your slide:** Two columns — Conclusions (6 bullet points) and Limitations (5 bullet points).
**Purpose:** The "so what" and "what's missing." Stating limitations proactively shows intellectual maturity and preempts committee questions.

### 17-18. References + Closing
**Your slide:** 69 sources, then a closing slide with contact info.
**Purpose:** Signals depth of literature engagement. The sheer volume (69 sources) reinforces that this is a serious piece of work.

---

## The Reusable Structure

Use this as a skeleton for any research or analytical presentation:

```
PHASE 1: SET THE STAGE (slides 1-3)
  [Title]           — Who, what, when
  [Key Terms]       — Define 2-3 concepts the audience needs
  [Why It Matters]  — Show a tension, gap, or opportunity in the field

PHASE 2: DEFINE THE MISSION (slides 4-5)
  [Problem & Goal]  — One clear problem, one goal, tasks with deliverables
  [Theory/Lit]      — Compressed background showing you know the field

PHASE 3: SHOW THE WORK (slides 6-9)
  [Data]            — What you studied, how much, where it came from
  [Tools/Models]    — What you used and why (with selection criteria)
  [Method]          — How the experiment/analysis was designed
  [Evaluation]      — How you measured success (scoring, benchmarks)

PHASE 4: DELIVER THE EVIDENCE (slides 10-14)
  [Finding 1]       — One claim + one visual proof
  [Finding 2]       — One claim + one visual proof
  [Finding 3]       — One claim + one visual proof
  [...repeat as needed, one finding per slide...]
  [Summary Table]   — Scoreboard of all hypotheses/findings

PHASE 5: LAND THE PLANE (slides 15-17)
  [Conclusions]     — What you proved, practical implications
  [Limitations]     — What you didn't cover, future work
  [References]      — Full bibliography
```

### Key Principles From This Structure

- **One idea per slide in the results section.** Never stack multiple findings on one slide.
- **Every claim needs a visual.** Chart, table, diagram, flowchart — no text-only result slides.
- **The "tension" slide early on is crucial.** It's what makes the audience care. Frame it as: "X is valuable but broken, Y is powerful but unproven — what happens when we combine them?"
- **Tasks-to-deliverables tables** signal planning rigor better than plain bullet lists.
- **State limitations yourself** before someone else does. It's a strength, not a weakness.
- **Hypothesis scoreboard** near the end gives closure. Partial rejections add credibility.
- **Keep theory compressed** (1 slide max for a defense, 2-3 for a longer talk). The audience came for your findings, not a textbook recap.
