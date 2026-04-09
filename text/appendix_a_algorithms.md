# Appendix A: Supplementary Algorithms

## A.1 Patch Merging Procedure

When multiple failures are fixed independently in parallel during a single sweep, the resulting patches may overlap, conflict, or duplicate each other. Algorithm 3 formalizes the merger procedure that consolidates winning patches into a coherent global state. The merger operates as a stateful LLM session with access to only the write-oriented patch tools---it cannot read tool source code or edit preprocessors, since its role is to apply, deduplicate, and compact the patches proposed by individual teacher sessions.

\begin{algorithm}
\caption{MergePatches}\label{alg:merge-patches}
\begin{algorithmic}[1]
\Require global state $\sigma = (\pi, \mathcal{S}, \mathcal{C})$, winning fixes $W$, merger model $M_t$
\Ensure merged state $\sigma'$
\State $\text{diffs} \gets \textsc{FormatPatchDiffs}(W)$ \Comment{per-fix: diagnosis + patch old/new text}
\State $\text{ctx} \gets \textsc{MergerPrompt}(\sigma, \text{diffs})$ \Comment{instructions: apply, deduplicate, compact}
\State $\text{tools} \gets \{\texttt{patch\_prompt},\, \texttt{patch\_tool}\}$ \Comment{write-only; no read or code tools}
\For{$\text{round} = 1$ \textbf{to} $R_\text{merge}$}
    \State $\text{calls} \gets \textsc{CallLLM}(M_t, \text{ctx}, \text{tools})$
    \If{$\text{calls} = \emptyset$} \textbf{break} \Comment{merger finished applying changes}
    \EndIf
    \For{\textbf{each} $\text{call} \in \text{calls}$}
        \State $\sigma, \text{feedback} \gets \textsc{ApplyAndValidate}(\sigma, \text{call})$ \Comment{JSON validity for schemas}
        \State $\text{ctx} \gets \text{ctx} \oplus \text{feedback}$
    \EndFor
\EndFor
\State \Return $\sigma$
\end{algorithmic}
\end{algorithm}

The merger prompt instructs the LLM to: (1) apply all proposed patches, combining overlapping ones; (2) deduplicate rules already present in the prompt or duplicated across fixes; (3) compact verbose additions into concise statements while preserving semantic intent; and (4) position critical rules at the beginning or end of the prompt rather than burying them. Each proposed patch is presented with its originating task's diagnosis (truncated to 600 characters) and labeled by type: instruction (prompt patch), tool (schema patch), or guardrail (preprocessor patch). The merger uses the same teacher model ($M_t$) with a lower temperature (0.2 versus 0.3 for the teacher) to favor deterministic application over creative diagnosis.
