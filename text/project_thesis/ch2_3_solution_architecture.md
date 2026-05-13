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

Algorithm 1 formalizes the outer loop. Let $\sigma = (\pi, \mathcal{S}, \mathcal{C})$ denote the evolved state---the system prompt, the dictionary of tool schemas, and the dictionary of tool preprocessors, respectively. $\text{Pass}(\mathbf{r})$ holds if and only if all $T$ trials achieve a perfect reward: $\forall\, t \in \{1,\dots,T\}: r_t = 1.0$.

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

In the **validation step**, the student is re-run on the same task with the patches applied for multiple trials. A fix is accepted only if the task passes unanimously---all trials achieve a perfect reward of 1.0. If not, all patches are reverted and the teacher receives the new conversation trace and reward breakdown, and is asked to try again. @Fig:inner-loop diagrams this per-failure fix loop.

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

**Tool preprocessors** are sandboxed Python functions that transform tool-call arguments before execution. Every tool starts with an identity preprocessor. The teacher can modify the code to add defensive input coercion---ensuring an ID field has the correct prefix, casting strings to integers, normalizing date formats. Preprocessors are sandboxed: a static analysis pass rejects forbidden constructs (imports, eval, exec, file I/O), the execution namespace restricts available builtins, and runtime exceptions fall back to the original arguments.

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

Classification is automated: the teacher includes the failure type in its diagnostic text, and the category is extracted by string matching. This is a heuristic---the implementation takes the first match, defaulting to REASONING_ERROR when none is found. The taxonomy enables per-category analysis of which failure types are most responsive to each patch surface.

### Quality Assurance

Several mechanisms ensure patch quality:

- **Unanimous validation:** A fix is accepted only if the patched student passes the task unanimously across all trials (each achieving reward 1.0). Partial improvements are not accepted. This prevents fragile patches from entering the global state.
- **LLM-based deduplication:** The merger session identifies and removes redundant patches that arise when multiple teacher sessions independently discover the same fix.
- **State persistence and rollback:** The complete evolved state is serialized to JSON after each iteration. Loading this state reconstructs the exact evolved agent. Any prior state can be restored.
- **Task locking:** After the first evaluation, task IDs are locked and reused for all subsequent iterations, so pass-rate changes reflect patches, not sampling variation.
