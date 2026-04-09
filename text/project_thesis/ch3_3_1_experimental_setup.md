## 3.3 Experimental Results

This section presents the results of testing the DPV framework (EDP Phase 6: Test Solution). The experimental setup described in Section 3.2 is executed across three scales and three student models to evaluate whether the framework achieves the project objectives defined in the Introduction.

### 3.3.1 Experimental Setup

All experiments use the airline domain of τ²-bench with the configuration described in Section 3.2. Three student models are evaluated:

- **Qwen3 30B-A3B** (non-thinking mode): a mixture-of-experts model with 30 billion total parameters and 3 billion active. Represents a weak non-thinking student with moderate baseline capability.
- **Qwen3.5 Flash**: a newer-generation model in the Qwen family with substantially stronger instruction following and tool-use capabilities. Represents a stronger non-thinking student to test how baseline capability affects the framework's value.
- **GLM 4.7 Flash**: a dense model from the GLM family with moderate instruction-following capability but distinct architectural characteristics from the Qwen models. Included to test whether the framework generalises beyond a single model family and to provide a third data point for the relationship between baseline capability and evolution effectiveness.

The teacher model is Kimi K2.5 in all experiments, and the user simulator is Qwen3 30B-A3B. Each experiment runs the evolution loop for up to three sweeps with up to two retries per failed task per sweep. Every task is evaluated with three trials to capture stochastic variation; a task is considered passing in a given sweep if it passes in at least two of three trials (majority vote, i.e., task $i$ passes iff $\sum_{t=1}^{3} \mathbb{1}[r_i^{(t)} = 1.0] \geq 2$). The seed is fixed at 42 throughout. Task IDs are locked after the first evaluation so that pass-rate changes between sweeps reflect the effect of accumulated patches, not sampling variation.

The experiments span three scales and eight conditions:

| Scale | Task IDs | Qwen3 30B | Q3.5 Flash | GLM 4.7 |
|-------|----------|-----------|------------|---------|
| 5 | 0, 1, 3, 4, 5 | Done | Done (base only) | Done |
| 10 | 0--5, 7, 9--12 | Done | Done | Done |
| 20 | 0--5, 7, 9--12, 14, 15, 17, 20, 21, 23, 27, 28, 33, 34 | Done | Done | Dropped |

: Experimental conditions across scales and models. All other parameters (teacher, user simulator, seed, sweep count) are identical. GLM 4.7 Flash is dropped at 20 tasks due to poor performance at 10 tasks (see Section 3.3.3.3). {#tbl:conditions}

The scaling sequence is deliberate. If the evolution framework captures task-specific fixes that do not generalise, then gains should be largest when the task set is smallest---each fix represents a larger share of the total---and should diminish as the denominator grows. The multi-model comparison tests a complementary question: if a stronger student already passes most tasks at baseline, does the framework still provide value, and does it address qualitatively different failure modes? The inclusion of GLM 4.7 Flash tests whether the framework generalises beyond the Qwen model family.
