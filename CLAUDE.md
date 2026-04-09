# Thesis Project Notes

## Statistical Analysis

- `analysis/statistical_tests.py` runs H1/H2/H3 hypothesis tests on actual experiment data from `results/runs/*.json`
- **FRONTIER_RATE is a placeholder (0.80)** in the H3 gap closure analysis. Must be replaced with the actual Kimi K2.5 pass rate on the airline domain from a frontier evaluation sweep before reporting final results.
- The script uses sweep 1 as baseline and sweep 3 (final) as evolved condition. A sensitivity analysis against the best post-baseline sweep is also included.

## Experiments Registry

Student models and their run IDs (all `results/runs/airline_20260308_*.json`):
- Qwen3 30B-A3B: 183440 (5t), 191630 (10t), 201356 (20t)
- Qwen3.5 Flash: 204715 (5t), 205019 (10t), 214250 (20t)
- GLM 4.7 Flash: 230845 (5t), 234047 (10t)

GLM 4.7 Flash regresses under evolution — the framework does not work for all models.
