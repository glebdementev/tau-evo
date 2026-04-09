"""
Compute statistical hypothesis tests from sweep_heatmap.json files.

The original run JSONs are not in the repo, but the Plotly heatmap JSONs
contain the full per-task, per-trial pass/fail data in their hovertext.
This script parses those, reconstructs SweepData objects, and runs
the same H1/H2/H3 tests as statistical_tests.py.

Usage:
    python analysis/run_stats_from_heatmaps.py
"""

import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy import stats

RUNS_DIR = Path(__file__).parent.parent / "runs"

# Map directory names to (model_key, n_tasks, label)
EXPERIMENTS = {
    "5":                ("qwen3", 5, "Qwen3 30B, 5t"),
    "10":               ("qwen3", 10, "Qwen3 30B, 10t"),
    "20":               ("qwen3", 20, "Qwen3 30B, 20t"),
    "glm47_5":          ("glm4.7", 5, "GLM 4.7, 5t"),
    "glm47_10":         ("glm4.7", 10, "GLM 4.7, 10t"),
    "qwen35-flash_10":  ("qwen3.5", 10, "Qwen3.5 Flash, 10t"),
    "qwen35-flash_20":  ("qwen3.5", 20, "Qwen3.5 Flash, 20t"),
}

# Fix data: (model, n_tasks) -> list of (n_genuinely_failing, n_fixed) per experiment
# Extracted from the thesis tables (ch3_3_*.md)
FIX_DATA = {
    ("qwen3", 5):   (4, 4),    # 4 failing at baseline, all 4 fixed eventually
    ("qwen3", 10):  (7, 5),    # 7 failing (excl T4 which passes), 5 fixed
    ("qwen3", 20):  (15, 8),   # 15 failing, 8 fixed
    ("qwen3.5", 10): (5, 4),   # 5 failing, 4 fixed (5,11,12,7,9 fail; 5,11,12 fixed + T10 regressed)
    ("qwen3.5", 20): (11, 5),  # 11 failing, 5 unique fixed
    ("glm4.7", 5):  (3, 3),    # 3 failing, 3 fixed (then regressed)
    ("glm4.7", 10): (5, 0),    # 5 failing, 0 fixed
}


def parse_heatmap(path: Path) -> dict[str, dict[str, list[float]]]:
    """
    Parse sweep_heatmap.json -> {sweep_name: {task_id: [trial_rewards]}}.

    The hovertext array has shape [n_sweeps][n_tasks * 3_trials],
    with entries like "Task 0 attempt 1: Pass" or "Task 12 attempt 2: Fail".
    """
    data = json.loads(path.read_text())
    trace = data["data"][0]
    hovertext = trace["hovertext"]  # [sweep][flat_trial_index]
    y_labels = trace["y"]           # ["Sweep 1", "Sweep 2", "Sweep 3"]

    result = {}
    for sweep_idx, sweep_label in enumerate(y_labels):
        task_rewards = {}
        for entry in hovertext[sweep_idx]:
            m = re.match(r"Task (\d+) attempt (\d+): (Pass|Fail)", entry)
            if not m:
                continue
            task_id = m.group(1)
            reward = 1.0 if m.group(3) == "Pass" else 0.0
            task_rewards.setdefault(task_id, []).append(reward)
        result[sweep_label] = task_rewards

    return result


def paired_ttest(baseline: dict, evolved: dict) -> dict:
    """Paired one-sided t-test on per-task trial-pass-rate deltas."""
    common = sorted(set(baseline) & set(evolved))
    base_rates = {t: np.mean(baseline[t]) for t in common}
    evol_rates = {t: np.mean(evolved[t]) for t in common}
    deltas = np.array([evol_rates[t] - base_rates[t] for t in common])
    n = len(deltas)
    mean_d = deltas.mean()
    std_d = deltas.std(ddof=1)

    if std_d == 0 or n < 2:
        return {"n": n, "mean_delta": mean_d, "t": np.inf if mean_d > 0 else 0,
                "p": 0.0 if mean_d > 0 else 1.0, "d": np.inf if mean_d > 0 else 0}

    t_stat, p_two = stats.ttest_1samp(deltas, 0.0)
    p_one = p_two / 2 if t_stat > 0 else 1.0 - p_two / 2
    cohens_d = mean_d / std_d

    return {"n": n, "mean_delta": mean_d, "t": t_stat, "p": p_one, "d": cohens_d,
            "deltas": deltas,
            "base_rate": np.mean([np.mean(baseline[t]) for t in common]),
            "evol_rate": np.mean([np.mean(evolved[t]) for t in common])}


def wilcoxon_test(baseline: dict, evolved: dict) -> dict:
    common = sorted(set(baseline) & set(evolved))
    deltas = np.array([np.mean(evolved[t]) - np.mean(baseline[t]) for t in common])
    nonzero = deltas[deltas != 0]
    if len(nonzero) < 6:
        return {"note": f"too few nonzero differences ({len(nonzero)})"}
    w, p = stats.wilcoxon(nonzero, alternative="greater")
    return {"W": w, "p": p, "n_nonzero": len(nonzero)}


def mcnemar_test(baseline: dict, evolved: dict) -> dict:
    common = sorted(set(baseline) & set(evolved))
    b = c = 0  # b=regressed, c=fixed
    for t in common:
        bp = all(r == 1.0 for r in baseline[t])
        ep = all(r == 1.0 for r in evolved[t])
        if bp and not ep: b += 1
        elif not bp and ep: c += 1
    n_disc = b + c
    if n_disc == 0:
        return {"c": c, "b": b, "p": 1.0}
    p = stats.binomtest(c, n_disc, 0.5, alternative="greater").pvalue
    return {"c": c, "b": b, "p": p}


def bootstrap_gap_closure(baseline: dict, evolved: dict, F: float,
                          n_boot: int = 10000, seed: int = 42) -> dict:
    rng = np.random.RandomState(seed)
    common = sorted(set(baseline) & set(evolved))
    n = len(common)
    base_r = np.array([np.mean(baseline[t]) for t in common])
    evol_r = np.array([np.mean(evolved[t]) for t in common])

    B = base_r.mean()
    K = evol_r.mean()
    G = (K - B) / (F - B) if F > B else np.nan

    G_boot = []
    for _ in range(n_boot):
        idx = rng.choice(n, size=n, replace=True)
        Bb = base_r[idx].mean()
        Kb = evol_r[idx].mean()
        if F > Bb:
            G_boot.append((Kb - Bb) / (F - Bb))
    G_boot = np.array(G_boot)
    ci = (np.percentile(G_boot, 2.5), np.percentile(G_boot, 97.5))
    p_gt_25 = np.mean(G_boot > 0.25)

    return {"B": B, "K": K, "F": F, "G": G, "ci": ci, "P_gt_25": p_gt_25}


def cochran_armitage(successes, totals, scores=None):
    k = len(successes)
    if scores is None:
        scores = list(range(k))
    n = np.array(totals, dtype=float)
    x = np.array(successes, dtype=float)
    t = np.array(scores, dtype=float)
    N = n.sum()
    p_hat = x.sum() / N
    t_bar = np.sum(n * t) / N
    num = np.sum(t * (x - n * p_hat))
    den = p_hat * (1 - p_hat) * (np.sum(n * t**2) - N * t_bar**2)
    if den <= 0:
        return {"Z": 0, "p": 1.0}
    Z = num / np.sqrt(den)
    p = stats.norm.cdf(Z)  # left tail = declining
    return {"Z": Z, "p": p}


def main():
    # Load all experiments
    experiments = {}
    for dirname, (model, n_tasks, label) in EXPERIMENTS.items():
        hm_path = RUNS_DIR / dirname / "sweep_heatmap.json"
        if not hm_path.exists():
            print(f"  SKIP: {hm_path}")
            continue
        sweeps = parse_heatmap(hm_path)
        experiments[(model, n_tasks)] = (label, sweeps)

    print(f"Loaded {len(experiments)} experiments.\n")

    # ═══════════════════════════════════════════════════════════════════════
    # H1: EFFECTIVENESS
    # ═══════════════════════════════════════════════════════════════════════
    print("=" * 80)
    print("H1: EFFECTIVENESS — Evolved agent pass rate > Baseline")
    print("    Paired one-sided t-test on per-task trial-pass-rate deltas")
    print("=" * 80)

    print(f"\n  {'Experiment':<24} {'n':>3} {'Base%':>6} {'Evol%':>6} "
          f"{'Δ':>7} {'t':>7} {'p(>0)':>8} {'d':>6} {'Sig':>4}")
    print("  " + "-" * 76)

    # Primary: sweep 1 vs sweep 3 (final)
    all_deltas_improving = []
    for (model, n_tasks), (label, sweeps) in sorted(experiments.items()):
        sweep_names = sorted(sweeps.keys())
        if len(sweep_names) < 2:
            continue
        baseline = sweeps[sweep_names[0]]
        evolved = sweeps[sweep_names[-1]]
        r = paired_ttest(baseline, evolved)
        sig = "***" if r["p"] < 0.001 else "**" if r["p"] < 0.01 else "*" if r["p"] < 0.05 else ""
        print(f"  {label:<24} {r['n']:>3} {100*r['base_rate']:>5.0f}% {100*r['evol_rate']:>5.0f}% "
              f"{r['mean_delta']:>+7.3f} {r['t']:>7.3f} {r['p']:>8.4f} {r['d']:>6.2f} {sig:>4}")
        # Collect for pooled (exclude GLM 10t which regresses)
        if not (model == "glm4.7" and n_tasks == 10):
            all_deltas_improving.extend(r["deltas"])

    # Sensitivity: sweep 1 vs best post-baseline
    print(f"\n  Sensitivity: sweep 1 vs best post-baseline sweep")
    for (model, n_tasks), (label, sweeps) in sorted(experiments.items()):
        sweep_names = sorted(sweeps.keys())
        if len(sweep_names) < 3:
            continue
        baseline = sweeps[sweep_names[0]]
        # Find best sweep by trial pass rate
        best_name = sweep_names[1]
        best_rate = np.mean([np.mean(v) for v in sweeps[best_name].values()])
        for sn in sweep_names[2:]:
            rate = np.mean([np.mean(v) for v in sweeps[sn].values()])
            if rate > best_rate:
                best_rate = rate
                best_name = sn
        if best_name == sweep_names[-1]:
            continue  # same as primary
        r = paired_ttest(baseline, sweeps[best_name])
        sig = "*" if r["p"] < 0.05 else ""
        print(f"  {label:<24} [{best_name}] {100*r['base_rate']:.0f}% → {100*r['evol_rate']:.0f}%, "
              f"Δ={r['mean_delta']:+.3f}, t={r['t']:.3f}, p={r['p']:.4f} {sig}")

    # Wilcoxon and McNemar
    print(f"\n  {'Experiment':<24} {'Wilcoxon p':>11} {'McNemar c/b':>12} {'McNemar p':>10}")
    print("  " + "-" * 60)
    for (model, n_tasks), (label, sweeps) in sorted(experiments.items()):
        sweep_names = sorted(sweeps.keys())
        if len(sweep_names) < 2:
            continue
        baseline = sweeps[sweep_names[0]]
        evolved = sweeps[sweep_names[-1]]
        wx = wilcoxon_test(baseline, evolved)
        mc = mcnemar_test(baseline, evolved)
        wx_str = f"{wx['p']:.4f}" if "p" in wx else wx.get("note", "N/A")
        print(f"  {label:<24} {wx_str:>11} {mc['c']}/{mc['b']:<8} {mc['p']:>10.4f}")

    # Pooled
    if all_deltas_improving:
        d = np.array(all_deltas_improving)
        t_stat, p_two = stats.ttest_1samp(d, 0.0)
        p_one = p_two / 2 if t_stat > 0 else 1 - p_two / 2
        cd = d.mean() / d.std(ddof=1)
        sig = "***" if p_one < 0.001 else "**" if p_one < 0.01 else "*" if p_one < 0.05 else ""
        print(f"\n  Pooled (all improving conditions, excl GLM 10t):")
        print(f"  n={len(d)}, mean Δ={d.mean():.3f}, t={t_stat:.3f}, "
              f"p={p_one:.4f}, Cohen's d={cd:.2f} {sig}")

    # ═══════════════════════════════════════════════════════════════════════
    # H2: DIMINISHING RETURNS
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("H2: DIMINISHING RETURNS — Fix success rate declines with pool size")
    print("    Cochran-Armitage trend test")
    print("=" * 80)

    for model_key in ["qwen3", "qwen3.5", "glm4.7"]:
        sizes, succs, tots = [], [], []
        for nt in [5, 10, 20]:
            key = (model_key, nt)
            if key in FIX_DATA:
                failing, fixed = FIX_DATA[key]
                sizes.append(nt)
                succs.append(fixed)
                tots.append(failing)

        if len(sizes) < 2:
            continue

        model_label = {"qwen3": "Qwen3 30B-A3B", "qwen3.5": "Qwen3.5 Flash",
                       "glm4.7": "GLM 4.7 Flash"}[model_key]
        print(f"\n  {model_label}:")
        for sz, s, t in zip(sizes, succs, tots):
            print(f"    Pool {sz:>2}: {s}/{t} ({100*s/t:.0f}%)")

        if len(sizes) >= 3:
            ca = cochran_armitage(succs, tots, scores=sizes)
            print(f"    Cochran-Armitage Z = {ca['Z']:.3f}, p(declining) = {ca['p']:.4f}")
        else:
            table = [[succs[0], tots[0] - succs[0]], [succs[1], tots[1] - succs[1]]]
            _, p = stats.fisher_exact(table, alternative="greater")
            print(f"    Fisher exact (smaller > larger): p = {p:.4f}")

    # ═══════════════════════════════════════════════════════════════════════
    # H3: GAP CLOSURE
    # ═══════════════════════════════════════════════════════════════════════
    print("\n" + "=" * 80)
    print("H3: GAP CLOSURE >= 25%")
    print("    Cluster bootstrap CI (10,000 resamples)")
    print("    NOTE: F = 0.80 is a PLACEHOLDER — replace with actual Kimi K2.5 rate")
    print("=" * 80)

    F = 0.80
    print(f"\n  {'Experiment':<24} {'B':>5} {'K':>5} {'F':>5} {'G':>6} "
          f"{'95% CI':>16} {'P(G>25%)':>9}")
    print("  " + "-" * 72)

    for (model, n_tasks), (label, sweeps) in sorted(experiments.items()):
        sweep_names = sorted(sweeps.keys())
        if len(sweep_names) < 2:
            continue
        baseline = sweeps[sweep_names[0]]
        # Use best post-baseline sweep for gap closure
        best_name = sweep_names[1]
        best_rate = np.mean([np.mean(v) for v in sweeps[best_name].values()])
        for sn in sweep_names[2:]:
            rate = np.mean([np.mean(v) for v in sweeps[sn].values()])
            if rate > best_rate:
                best_rate = rate
                best_name = sn
        evolved = sweeps[best_name]
        gc = bootstrap_gap_closure(baseline, evolved, F)
        if np.isnan(gc["G"]):
            print(f"  {label:<24} {gc['B']:>5.2f} {gc['K']:>5.2f} {gc['F']:>5.2f} {'undef':>6} "
                  f"{'---':>16} {'---':>9}")
        else:
            print(f"  {label:<24} {gc['B']:>5.2f} {gc['K']:>5.2f} {gc['F']:>5.2f} {gc['G']:>6.2f} "
                  f"[{gc['ci'][0]:>5.2f}, {gc['ci'][1]:>5.2f}]     {gc['P_gt_25']:>8.1%}")


if __name__ == "__main__":
    main()
