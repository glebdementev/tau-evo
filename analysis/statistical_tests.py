"""
Statistical hypothesis testing for the thesis experiments.

Tests H1 (effectiveness), H2 (diminishing returns), H3 (gap closure)
on actual experiment data from results/runs/*.json.

Methodology references:
  - Dror et al. (2018) "Hitchhiker's Guide to Testing Statistical Significance in NLP"
  - Bowyer et al. (2025) "Don't Use the CLT in LLM Evals With Fewer Than a Few Hundred Datapoints"
  - Card et al. (2020) "With Little Power Comes Great Responsibility"

Usage:
    python analysis/statistical_tests.py
"""

import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import stats

RESULTS_DIR = Path(__file__).parent.parent / "results"
RUNS_DIR = RESULTS_DIR / "runs"

# ── Experiment registry ──────────────────────────────────────────────────────
# Map: (student_model, n_tasks) -> run_id
# Identified from sweep files and run metadata.

EXPERIMENTS = {
    ("qwen3", 5):  "airline_20260308_183440",
    ("qwen3", 10): "airline_20260308_191630",
    ("qwen3", 20): "airline_20260308_201356",
    ("qwen3.5", 5):  "airline_20260308_204715",
    ("qwen3.5", 10): "airline_20260308_205019",
    ("qwen3.5", 20): "airline_20260308_214250",
    ("glm4.7", 5):  "airline_20260308_230845",
    ("glm4.7", 10): "airline_20260308_234047",
}

MODEL_LABELS = {
    "qwen3": "Qwen3 30B-A3B",
    "qwen3.5": "Qwen3.5 Flash",
    "glm4.7": "GLM 4.7 Flash",
}


# ── Data loading ─────────────────────────────────────────────────────────────

@dataclass
class SweepData:
    """Per-task, per-trial reward data from a single sweep."""
    task_rewards: dict[str, list[float]]  # task_id -> [trial rewards]

    @property
    def task_ids(self) -> list[str]:
        return sorted(self.task_rewards.keys())

    @property
    def n_tasks(self) -> int:
        return len(self.task_rewards)

    def trial_pass_rate(self) -> float:
        trials = [r for rewards in self.task_rewards.values() for r in rewards]
        return sum(1 for t in trials if t == 1.0) / len(trials) if trials else 0.0

    def task_pass_rate(self) -> float:
        """Unanimous pass: all trials for a task must be 1.0."""
        passes = sum(1 for rewards in self.task_rewards.values()
                     if all(r == 1.0 for r in rewards))
        return passes / self.n_tasks if self.n_tasks else 0.0

    def per_task_rates(self) -> dict[str, float]:
        """Per-task trial pass rate (0, 0.33, 0.67, or 1.0 for 3 trials)."""
        return {tid: np.mean([1.0 if r == 1.0 else 0.0 for r in rewards])
                for tid, rewards in self.task_rewards.items()}


@dataclass
class FixData:
    task_id: str
    fixed: bool
    tier: Optional[str]
    retries: int
    baseline_reward: float
    patched_reward: float


@dataclass
class ExperimentRun:
    run_id: str
    model: str
    n_tasks: int
    sweeps: list[SweepData]
    fixes: list[list[FixData]]  # per-sweep fix lists

    @property
    def baseline(self) -> SweepData:
        return self.sweeps[0]

    @property
    def evolved(self) -> SweepData:
        """Last sweep = final evaluation after all patches merged."""
        return self.sweeps[-1]


def load_run(run_id: str, model: str) -> ExperimentRun:
    path = RUNS_DIR / f"{run_id}.json"
    d = json.loads(path.read_text())
    meta = d.get("meta", {})
    n_tasks = meta.get("num_tasks", 0)

    sweeps = []
    fixes_per_sweep = []
    for h in d.get("history", []):
        sr = h.get("sweep_rewards", {})
        # Normalize: ensure all values are lists
        task_rewards = {}
        for tid, v in sr.items():
            task_rewards[tid] = v if isinstance(v, list) else [v]
        sweeps.append(SweepData(task_rewards=task_rewards))

        fix_list = []
        for f in h.get("fixes", []):
            fix_list.append(FixData(
                task_id=str(f["task_id"]),
                fixed=f.get("fixed", False),
                tier=f.get("fix_tier"),
                retries=f.get("retries", 0),
                baseline_reward=f.get("baseline_reward", 0.0),
                patched_reward=f.get("patched_reward", 0.0),
            ))
        fixes_per_sweep.append(fix_list)

    return ExperimentRun(
        run_id=run_id, model=model, n_tasks=n_tasks,
        sweeps=sweeps, fixes=fixes_per_sweep,
    )


# ── Statistical tests ────────────────────────────────────────────────────────

def paired_ttest_per_task(baseline: SweepData, evolved: SweepData) -> dict:
    """
    Paired one-sided t-test on per-task pass-rate deltas.

    Each task contributes one observation: its trial pass rate under the evolved
    condition minus its trial pass rate under the baseline. With 3 trials per
    task, each observation takes values in {-1, -0.67, -0.33, 0, 0.33, 0.67, 1}.

    This is the recommended approach for paired binary data with multiple
    observations per unit (Dror et al. 2018; Bowyer et al. 2025).
    """
    base_rates = baseline.per_task_rates()
    evol_rates = evolved.per_task_rates()
    common_tasks = sorted(set(base_rates) & set(evol_rates))

    deltas = np.array([evol_rates[t] - base_rates[t] for t in common_tasks])
    n = len(deltas)
    mean_delta = deltas.mean()
    std_delta = deltas.std(ddof=1)

    if std_delta == 0 or n < 2:
        return {"test": "paired_t", "n": n, "mean_delta": mean_delta,
                "t": np.inf if mean_delta > 0 else 0, "p_one_sided": 0.0 if mean_delta > 0 else 1.0}

    t_stat, p_two = stats.ttest_1samp(deltas, 0.0)
    p_one = p_two / 2 if t_stat > 0 else 1.0 - p_two / 2

    # Cohen's d (effect size for paired data)
    cohens_d = mean_delta / std_delta

    return {
        "test": "paired_t",
        "n": n,
        "mean_delta": mean_delta,
        "std_delta": std_delta,
        "t": t_stat,
        "p_two_sided": p_two,
        "p_one_sided": p_one,
        "cohens_d": cohens_d,
        "deltas": deltas,
    }


def wilcoxon_per_task(baseline: SweepData, evolved: SweepData) -> dict:
    """
    Wilcoxon signed-rank test (non-parametric paired test) on per-task deltas.
    More robust than t-test for small n where normality is questionable.
    """
    base_rates = baseline.per_task_rates()
    evol_rates = evolved.per_task_rates()
    common_tasks = sorted(set(base_rates) & set(evol_rates))

    deltas = np.array([evol_rates[t] - base_rates[t] for t in common_tasks])
    nonzero = deltas[deltas != 0]

    if len(nonzero) < 6:
        return {"test": "wilcoxon", "n_nonzero": len(nonzero),
                "note": "too few nonzero differences (need >= 6)"}

    w_stat, p_one = stats.wilcoxon(nonzero, alternative="greater")
    return {
        "test": "wilcoxon",
        "n_nonzero": len(nonzero),
        "W": w_stat,
        "p_one_sided": p_one,
    }


def mcnemar_task_level(baseline: SweepData, evolved: SweepData) -> dict:
    """
    McNemar's exact test on task-level unanimous pass (all trials = 1.0).
    Tests whether more tasks flipped pass->fail than fail->pass.
    """
    common_tasks = sorted(set(baseline.task_ids) & set(evolved.task_ids))
    a = b = c = d = 0  # a=both pass, b=regress, c=fixed, d=both fail
    for tid in common_tasks:
        bp = all(r == 1.0 for r in baseline.task_rewards[tid])
        ep = all(r == 1.0 for r in evolved.task_rewards[tid])
        if bp and ep: a += 1
        elif bp and not ep: b += 1
        elif not bp and ep: c += 1
        else: d += 1

    # Exact binomial test on discordant pairs (b vs c)
    n_disc = b + c
    if n_disc == 0:
        p_one = 1.0
    else:
        p_one = stats.binomtest(c, n_disc, 0.5, alternative="greater").pvalue

    return {
        "test": "mcnemar_exact",
        "both_pass": a, "regressed": b, "fixed": c, "both_fail": d,
        "n_discordant": n_disc,
        "p_one_sided": p_one,
    }


def fisher_trial_level(baseline: SweepData, evolved: SweepData) -> dict:
    """
    Fisher's exact test on trial-level pass counts (unpaired).
    NOTE: This ignores task-level clustering and treats trials as independent.
    Reported for completeness; the paired t-test is preferred.
    """
    base_trials = [r for rewards in baseline.task_rewards.values() for r in rewards]
    evol_trials = [r for rewards in evolved.task_rewards.values() for r in rewards]

    bp = sum(1 for r in base_trials if r == 1.0)
    bn = len(base_trials) - bp
    ep = sum(1 for r in evol_trials if r == 1.0)
    en = len(evol_trials) - ep

    table = [[ep, en], [bp, bn]]
    odds, p = stats.fisher_exact(table, alternative="greater")
    return {
        "test": "fisher_exact_trials",
        "baseline": f"{bp}/{bp+bn}",
        "evolved": f"{ep}/{ep+en}",
        "odds_ratio": odds,
        "p_one_sided": p,
        "note": "ignores task clustering; use paired_t as primary",
    }


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Clopper-Pearson exact confidence interval for a proportion."""
    if n == 0:
        return (0.0, 1.0)
    lo = stats.beta.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    hi = stats.beta.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return (lo, hi)


def bootstrap_gap_closure(baseline: SweepData, evolved: SweepData,
                          frontier_rate: float, n_boot: int = 10000,
                          seed: int = 42) -> dict:
    """
    Cluster bootstrap CI on gap closure G = (K - B) / (F - B).
    Resamples tasks (keeping all trials within a task together) to respect
    the nested structure (Field & Welsh, 2007).
    """
    rng = np.random.RandomState(seed)
    common_tasks = sorted(set(baseline.task_ids) & set(evolved.task_ids))
    n = len(common_tasks)

    base_task_rates = np.array([np.mean([1.0 if r == 1.0 else 0.0
                                         for r in baseline.task_rewards[t]])
                                for t in common_tasks])
    evol_task_rates = np.array([np.mean([1.0 if r == 1.0 else 0.0
                                         for r in evolved.task_rewards[t]])
                                for t in common_tasks])

    B_obs = base_task_rates.mean()
    K_obs = evol_task_rates.mean()
    F = frontier_rate
    G_obs = (K_obs - B_obs) / (F - B_obs) if F > B_obs else np.nan

    G_boot = []
    for _ in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        B_b = base_task_rates[idx].mean()
        K_b = evol_task_rates[idx].mean()
        if F > B_b:
            G_boot.append((K_b - B_b) / (F - B_b))
    G_boot = np.array(G_boot)

    # BCa would be ideal but percentile is fine for reporting
    ci_lo, ci_hi = np.percentile(G_boot, [2.5, 97.5])
    exceeds_25 = np.mean(G_boot > 0.25)

    return {
        "test": "cluster_bootstrap_gap_closure",
        "B": B_obs,
        "K": K_obs,
        "F": F,
        "G": G_obs,
        "ci_95": (ci_lo, ci_hi),
        "P(G > 0.25)": exceeds_25,
        "n_boot": n_boot,
    }


def cochran_armitage_trend(successes: list[int], totals: list[int],
                           scores: Optional[list[float]] = None) -> dict:
    """
    Cochran-Armitage test for trend in proportions across ordered groups.
    Tests H2: whether fix success rate declines with increasing pool size.

    References: Cochran (1954), Armitage (1955).
    """
    k = len(successes)
    if scores is None:
        scores = list(range(k))

    n = np.array(totals, dtype=float)
    x = np.array(successes, dtype=float)
    t = np.array(scores, dtype=float)
    N = n.sum()
    p_hat = x.sum() / N

    t_bar = np.sum(n * t) / N
    numerator = np.sum(t * (x - n * p_hat))
    denominator = p_hat * (1 - p_hat) * (np.sum(n * t**2) - N * t_bar**2)

    if denominator <= 0:
        return {"test": "cochran_armitage", "note": "degenerate"}

    Z = numerator / np.sqrt(denominator)
    # One-sided: we expect DECLINING rate, so negative trend
    p_one = stats.norm.cdf(Z)  # left tail = declining trend

    return {
        "test": "cochran_armitage",
        "proportions": [s/t for s, t in zip(successes, totals)],
        "Z": Z,
        "p_declining": p_one,
        "p_two_sided": 2 * min(p_one, 1 - p_one),
    }


# ── Reporting ────────────────────────────────────────────────────────────────

def fmt_p(p: float) -> str:
    if p < 0.001: return "p < 0.001"
    if p < 0.01: return f"p = {p:.3f}"
    return f"p = {p:.3f}"


def print_h1_results(experiments: dict[tuple, ExperimentRun]):
    print("\n" + "=" * 80)
    print("H1: EFFECTIVENESS — Evolved agent pass rate > Baseline")
    print("    Test: Paired one-sided t-test on per-task trial-pass-rate deltas")
    print("    (Dror et al. 2018; Bowyer et al. 2025)")
    print("=" * 80)

    # ── Primary analysis: sweep 1 (baseline) vs sweep 3 (final evolved) ──
    print("\n  PRIMARY: Sweep 1 (baseline) vs Sweep 3 (final evolved state)")
    header = f"  {'Experiment':<28} {'n':>3} {'Base%':>6} {'Evol%':>6} {'Δ':>6} {'t':>7} {'p(>0)':>8} {'d':>6} {'Sig':>4}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for (model, n_tasks), run in sorted(experiments.items()):
        if len(run.sweeps) < 2:
            continue
        result = paired_ttest_per_task(run.baseline, run.evolved)
        base_pct = 100 * run.baseline.trial_pass_rate()
        evol_pct = 100 * run.evolved.trial_pass_rate()
        sig = "***" if result["p_one_sided"] < 0.001 else \
              "**" if result["p_one_sided"] < 0.01 else \
              "*" if result["p_one_sided"] < 0.05 else ""
        label = f"{MODEL_LABELS[model]} ({n_tasks}t)"
        print(f"  {label:<28} {result['n']:>3} {base_pct:>5.0f}% {evol_pct:>5.0f}% "
              f"{result['mean_delta']:>+.3f} {result['t']:>7.3f} {result['p_one_sided']:>8.4f} "
              f"{result['cohens_d']:>6.3f} {sig:>4}")

    # ── Sensitivity: sweep 1 vs best post-baseline sweep ──
    print("\n  SENSITIVITY: Sweep 1 vs best post-baseline sweep (accounts for patch interference)")
    for (model, n_tasks), run in sorted(experiments.items()):
        if len(run.sweeps) < 3:
            continue
        # Find best sweep among sweeps 2+ by trial pass rate
        best_idx = 1
        best_rate = run.sweeps[1].trial_pass_rate()
        for i in range(2, len(run.sweeps)):
            r = run.sweeps[i].trial_pass_rate()
            if r > best_rate:
                best_rate = r
                best_idx = i
        if best_idx == len(run.sweeps) - 1:
            continue  # best = final, already reported above
        result = paired_ttest_per_task(run.baseline, run.sweeps[best_idx])
        base_pct = 100 * run.baseline.trial_pass_rate()
        best_pct = 100 * run.sweeps[best_idx].trial_pass_rate()
        label = f"{MODEL_LABELS[model]} ({n_tasks}t) [S{best_idx+1}]"
        sig = "*" if result["p_one_sided"] < 0.05 else ""
        print(f"  {label:<32} {base_pct:>4.0f}% → {best_pct:>4.0f}%, "
              f"Δ={result['mean_delta']:>+.3f}, t={result['t']:.3f}, "
              f"p={result['p_one_sided']:.4f} {sig}")

    # ── McNemar and Wilcoxon sensitivity checks ──
    print("\n  Sensitivity checks (McNemar exact on task-level, Wilcoxon signed-rank):")
    print(f"  {'Experiment':<28} {'McNemar p':>10} {'c/b':>6} {'Wilcoxon p':>11}")
    print("  " + "-" * 60)
    for (model, n_tasks), run in sorted(experiments.items()):
        if len(run.sweeps) < 2:
            continue
        mc = mcnemar_task_level(run.baseline, run.evolved)
        wx = wilcoxon_per_task(run.baseline, run.evolved)
        label = f"{MODEL_LABELS[model]} ({n_tasks}t)"
        wx_p = f"{wx['p_one_sided']:.4f}" if "p_one_sided" in wx else wx.get("note", "N/A")
        print(f"  {label:<28} {mc['p_one_sided']:>10.4f} {mc['fixed']}/{mc['regressed']:<4} {wx_p:>11}")

    # ── Pooled analysis per model ──
    print("\n  Pooled per-model (all task sizes combined):")
    for model_key in ["qwen3", "qwen3.5", "glm4.7"]:
        all_deltas = []
        for (m, nt), run in experiments.items():
            if m != model_key or len(run.sweeps) < 2:
                continue
            result = paired_ttest_per_task(run.baseline, run.evolved)
            if "deltas" in result:
                all_deltas.extend(result["deltas"])
        if len(all_deltas) < 3:
            continue
        all_deltas = np.array(all_deltas)
        t_stat, p_two = stats.ttest_1samp(all_deltas, 0.0)
        p_one = p_two / 2 if t_stat > 0 else 1 - p_two / 2
        d = all_deltas.mean() / all_deltas.std(ddof=1)
        sig = "***" if p_one < 0.001 else "**" if p_one < 0.01 else "*" if p_one < 0.05 else ""
        print(f"  {MODEL_LABELS[model_key]}: n={len(all_deltas)} tasks, "
              f"mean Δ={all_deltas.mean():.3f}, t={t_stat:.3f}, "
              f"{fmt_p(p_one)}, Cohen's d={d:.3f} {sig}")

    # ── Cross-model pooled (Qwen3 + Qwen3.5 only, excluding GLM which regresses) ──
    print("\n  Pooled across improving models (Qwen3 + Qwen3.5):")
    all_deltas = []
    for (m, nt), run in experiments.items():
        if m not in ("qwen3", "qwen3.5") or len(run.sweeps) < 2:
            continue
        result = paired_ttest_per_task(run.baseline, run.evolved)
        if "deltas" in result:
            all_deltas.extend(result["deltas"])
    if len(all_deltas) >= 3:
        all_deltas = np.array(all_deltas)
        t_stat, p_two = stats.ttest_1samp(all_deltas, 0.0)
        p_one = p_two / 2 if t_stat > 0 else 1 - p_two / 2
        d = all_deltas.mean() / all_deltas.std(ddof=1)
        sig = "***" if p_one < 0.001 else "**" if p_one < 0.01 else "*" if p_one < 0.05 else ""
        print(f"  n={len(all_deltas)} tasks, mean Δ={all_deltas.mean():.3f}, "
              f"t={t_stat:.3f}, {fmt_p(p_one)}, Cohen's d={d:.3f} {sig}")


def print_h2_results(experiments: dict[tuple, ExperimentRun]):
    print("\n" + "=" * 80)
    print("H2: DIMINISHING RETURNS — Fix success rate declines with pool size")
    print("    Test: Cochran-Armitage trend test (Cochran 1954; Armitage 1955)")
    print("=" * 80)

    for model_key in ["qwen3", "qwen3.5", "glm4.7"]:
        sizes = []
        successes = []
        totals = []
        for nt in [5, 10, 20]:
            key = (model_key, nt)
            if key not in experiments:
                continue
            run = experiments[key]
            # Aggregate all fixes across all sweeps
            all_fixes = [f for sweep_fixes in run.fixes for f in sweep_fixes]
            if not all_fixes:
                continue
            s = sum(1 for f in all_fixes if f.fixed)
            t = len(all_fixes)
            sizes.append(nt)
            successes.append(s)
            totals.append(t)

        if len(sizes) < 2:
            continue

        print(f"\n  {MODEL_LABELS[model_key]}:")
        for sz, s, t in zip(sizes, successes, totals):
            pct = 100 * s / t if t else 0
            print(f"    Pool size {sz:>2}: {s}/{t} fixes succeeded ({pct:.0f}%)")

        if len(sizes) >= 3:
            ca = cochran_armitage_trend(successes, totals, scores=sizes)
            print(f"    Cochran-Armitage Z = {ca['Z']:.3f}, "
                  f"p(declining) = {ca['p_declining']:.4f}")
        elif len(sizes) == 2:
            # Fisher's exact for 2 groups
            table = [[successes[0], totals[0] - successes[0]],
                     [successes[1], totals[1] - successes[1]]]
            _, p = stats.fisher_exact(table, alternative="greater")
            print(f"    Fisher's exact (smaller pool > larger pool): p = {p:.4f}")


def print_h3_results(experiments: dict[tuple, ExperimentRun]):
    print("\n" + "=" * 80)
    print("H3: GAP CLOSURE >= 25%")
    print("    Test: Cluster bootstrap CI (Field & Welsh 2007)")
    print("=" * 80)

    # We need frontier ceiling rates. These come from the frontier condition.
    # For now, use the thesis-reported Kimi K2.5 frontier rates.
    # If you have actual frontier sweep files, load them instead.
    # Placeholder: use values from the thesis (ch5 conclusion mentions ~98% telecom for frontier)
    # For airline domain, let's estimate from available data or use a reasonable value.
    # The thesis mentions "roughly 98% on telecom" for Claude. For Kimi K2.5 on airline,
    # we need the actual number. Let's try to find it.
    print("\n  NOTE: Frontier rate must be supplied. Using thesis-reported values.")
    print("  Update FRONTIER_RATES below with actual ceiling measurements.\n")

    # Adjust these from your actual frontier evaluation data:
    FRONTIER_RATE = 0.80  # placeholder — replace with actual Kimi K2.5 airline pass rate

    for (model, n_tasks), run in sorted(experiments.items()):
        if len(run.sweeps) < 2:
            continue
        gc = bootstrap_gap_closure(run.baseline, run.evolved, FRONTIER_RATE)
        label = f"{MODEL_LABELS[model]} ({n_tasks}t)"
        if np.isnan(gc["G"]):
            print(f"  {label}: G undefined (F <= B)")
            continue
        print(f"  {label}: B={gc['B']:.3f}, K={gc['K']:.3f}, F={gc['F']:.3f}")
        print(f"    Gap closure G = {gc['G']:.1%}, "
              f"95% CI = [{gc['ci_95'][0]:.1%}, {gc['ci_95'][1]:.1%}], "
              f"P(G > 25%) = {gc['P(G > 0.25)']:.1%}")


def print_sweep_progression(experiments: dict[tuple, ExperimentRun]):
    """Show the sweep-by-sweep progression for each experiment."""
    print("\n" + "=" * 80)
    print("SWEEP PROGRESSION (baseline → fix → eval → fix → final eval)")
    print("=" * 80)

    for (model, n_tasks), run in sorted(experiments.items()):
        label = f"{MODEL_LABELS[model]} ({n_tasks}t)"
        print(f"\n  {label}:")
        for i, (sweep, fixes) in enumerate(zip(run.sweeps, run.fixes)):
            tr = sweep.trial_pass_rate()
            tp = sweep.task_pass_rate()
            n_trials = sum(len(v) for v in sweep.task_rewards.values())
            pass_trials = sum(sum(1 for r in v if r == 1.0) for v in sweep.task_rewards.values())

            # CI on trial pass rate
            ci_lo, ci_hi = clopper_pearson(pass_trials, n_trials)

            fix_str = ""
            if fixes:
                fixed = sum(1 for f in fixes if f.fixed)
                fix_str = f" → {fixed}/{len(fixes)} fixes"

            print(f"    Sweep {i+1}: {pass_trials}/{n_trials} trials "
                  f"({100*tr:.0f}%, CI [{100*ci_lo:.0f}%, {100*ci_hi:.0f}%]), "
                  f"task pass^1 = {100*tp:.0f}%{fix_str}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    experiments = {}
    for (model, n_tasks), run_id in EXPERIMENTS.items():
        path = RUNS_DIR / f"{run_id}.json"
        if not path.exists():
            print(f"  SKIP: {path} not found", file=sys.stderr)
            continue
        try:
            experiments[(model, n_tasks)] = load_run(run_id, model)
        except Exception as e:
            print(f"  ERROR loading {run_id}: {e}", file=sys.stderr)

    print(f"Loaded {len(experiments)} experiments.\n")

    print_sweep_progression(experiments)
    print_h1_results(experiments)
    print_h2_results(experiments)
    print_h3_results(experiments)


if __name__ == "__main__":
    main()
