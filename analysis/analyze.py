"""
Анализ результатов: медиана, IQR, bootstrap 95% CI, Mann–Whitney, Cliff's δ.
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


def ci95(x):
    x = np.asarray(x)
    if len(x) < 3:
        return (np.nan, np.nan)
    res = stats.bootstrap((x,), np.median, confidence_level=0.95,
                          random_state=0, n_resamples=10000)
    return (res.confidence_interval.low, res.confidence_interval.high)


def cliffs_delta(a, b):
    a, b = np.asarray(a), np.asarray(b)
    gt = np.sum(a[:, None] > b[None, :])
    lt = np.sum(a[:, None] < b[None, :])
    return (gt - lt) / (len(a) * len(b))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/raw")
    parser.add_argument("--output", default="results/processed")
    args = parser.parse_args()

    raw = Path(args.input)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for m in raw.glob("*.json"):
        meta = json.loads(m.read_text())
        run_id = meta["run_id"]
        stats_csv = raw / f"{run_id}_stats.csv"
        if not stats_csv.exists():
            continue
        agg = pd.read_csv(stats_csv).query("Name == 'Aggregated'").iloc[0]
        rows.append({
            **meta["params"],
            "rep": meta["repetition"],
            "p50": agg["50%"],
            "p95": agg["95%"],
            "p99": agg["99%"],
            "rps": agg["Requests/s"],
            "fail": agg["Failure Count"],
        })

    if not rows:
        print("No runs found in", raw)
        return

    df = pd.DataFrame(rows)
    df.to_csv(out / "runs.csv", index=False)

    # Сводка: медиана, IQR, CI по p95
    summary = (df.groupby(["backend", "intensity", "cardinality"])["p95"]
               .agg(median="median",
                    iqr=lambda s: s.quantile(.75) - s.quantile(.25),
                    n="count"))
    ci = df.groupby(["backend", "intensity", "cardinality"])["p95"].apply(ci95)
    summary["ci_low"] = [c[0] for c in ci]
    summary["ci_high"] = [c[1] for c in ci]
    summary.to_csv(out / "summary_p95.csv")
    print(summary)

    # Mann–Whitney + Cliff's δ: Prometheus vs VictoriaMetrics на каждом уровне
    for (intensity, cardinality), g in df.groupby(["intensity", "cardinality"]):
        a = g.query("backend == 'prometheus'")["p95"]
        b = g.query("backend == 'victoriametrics'")["p95"]
        if len(a) < 2 or len(b) < 2:
            continue
        u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        delta = cliffs_delta(a.values, b.values)
        print(f"intensity={intensity}, cardinality={cardinality}: "
              f"Mann-Whitney p={p:.4f}, Cliff's δ={delta:+.3f}")

    # Улучшенный boxplot с разбивкой по интенсивности
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        # Создаем фигуру с двумя подграфиками (для 10 и 60 запросов/с)
        fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
        
        # Первый график: низкая нагрузка (10)
        df[df["intensity"] == 10].boxplot(column="p95", by=["backend", "cardinality"], ax=axes[0])
        axes[0].set_title("Intensity: 10 req/s")
        axes[0].set_xlabel("")
        axes[0].set_ylabel("p95 latency, ms")
        
        # Второй график: высокая нагрузка (60)
        df[df["intensity"] == 60].boxplot(column="p95", by=["backend", "cardinality"], ax=axes[1])
        axes[1].set_title("Intensity: 60 req/s")
        axes[1].set_xlabel("")
        axes[1].set_ylabel("")
        
        # Поворачиваем подписи на оси X и убираем лишний заголовок сверху
        for ax in axes:
            ax.tick_params(axis='x', rotation=45)
        
        plt.suptitle("") # Убираем автоматический заголовок pandas
        plt.suptitle("p95 latency by backend and cardinality (grouped by intensity)")
        plt.tight_layout()
        plt.savefig(out / "p95_boxplot.png", dpi=120)
        print("Saved plot:", out / "p95_boxplot.png")
    except Exception as e:
        print("Plot skipped:", e)