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
            "p75": agg["75%"],
            "p90": agg["90%"],
            "p95": agg["95%"],
            "p98": agg["98%"],
            "p99": agg["99%"],
            "p999": agg["99.9%"],
            "rps": agg["Requests/s"],
            "fail": agg["Failure Count"],
        })

    if not rows:
        print("No runs found in", raw)
        return

    df = pd.DataFrame(rows)
    df.to_csv(out / "runs.csv", index=False)

    # 1. Считаем медианы для ВСЕХ перцентилей
    summary = (df.groupby(["backend", "intensity", "cardinality"])[["p50", "p75", "p90", "p95", "p98", "p99", "p999"]]
               .median()
               .add_suffix("_median"))

    # 2. Считаем IQR для p95
    iqr = df.groupby(["backend", "intensity", "cardinality"])["p95"].apply(lambda s: s.quantile(.75) - s.quantile(.25))
    summary["p95_iqr"] = iqr

    # 3. Считаем количество повторов (n)
    summary["n"] = df.groupby(["backend", "intensity", "cardinality"]).size()

    # 4. Считаем 95% доверительный интервал (CI) для p95
    ci = df.groupby(["backend", "intensity", "cardinality"])["p95"].apply(ci95)
    summary["p95_ci_low"] = [c[0] for c in ci]
    summary["p95_ci_high"] = [c[1] for c in ci]

    # 5. Статистические тесты (Mann-Whitney + Cliff's delta)
    test_rows = []
    for (intensity, cardinality), g in df.groupby(["intensity", "cardinality"]):
        a = g.query("backend == 'prometheus'")["p95"]
        b = g.query("backend == 'victoriametrics'")["p95"]
        if len(a) >= 2 and len(b) >= 2:
            u, p_val = stats.mannwhitneyu(a, b, alternative="two-sided")
            delta = cliffs_delta(a.values, b.values)
            test_rows.append({
                "intensity": intensity, 
                "cardinality": cardinality,
                "p_value": p_val, 
                "cliffs_delta": delta
            })
            print(f"intensity={intensity}, cardinality={cardinality}: Mann-Whitney p={p_val:.4f}, Cliff's δ={delta:+.3f}")
            
    if test_rows:
        pd.DataFrame(test_rows).to_csv(out / "stats_tests.csv", index=False)
        print("Stats tests saved to stats_tests.csv")

    # Сохраняем и выводим итоговую таблицу
    summary.to_csv(out / "summary_metrics.csv")
    print("\n", summary)

    # 6. Генерация графиков
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        
        # График 1: Boxplot по интенсивностям (для p95)
        fig, axes = plt.subplots(1, 2, figsize=(12, 6), sharey=True)
        
        df[df["intensity"] == 10].boxplot(column="p95", by=["backend", "cardinality"], ax=axes[0])
        axes[0].set_title("Intensity: 10 req/s")
        axes[0].set_xlabel("")
        axes[0].set_ylabel("p95 latency, ms")
        
        df[df["intensity"] == 60].boxplot(column="p95", by=["backend", "cardinality"], ax=axes[1])
        axes[1].set_title("Intensity: 60 req/s")
        axes[1].set_xlabel("")
        axes[1].set_ylabel("")
        
        for ax in axes:
            ax.tick_params(axis='x', rotation=45)
        
        plt.suptitle("")
        plt.suptitle("p95 latency by backend and cardinality (grouped by intensity)")
        plt.tight_layout()
        plt.savefig(out / "p95_boxplot.png", dpi=120)
        print("Saved plot:", out / "p95_boxplot.png")

        # График 2: Все перцентили (Линейный график по медианам)
        # Берем данные для самой высокой нагрузки, чтобы показать рост задержки
        df_high = summary.reset_index()
        df_high = df_high[df_high["intensity"] == 60]
        
        percentiles = ["p50_median", "p75_median", "p90_median", "p95_median", "p98_median", "p99_median", "p999_median"]
        x_labels = ["p50", "p75", "p90", "p95", "p98", "p99", "p99.9"]
        
        plt.figure(figsize=(10, 6))
        for backend in ["prometheus", "victoriametrics"]:
            # Берем только строки для нужного backend и низкой кардинальности (для чистоты)
            subset = df_high[(df_high["backend"] == backend) & (df_high["cardinality"] == "low")]
            if not subset.empty:
                y_vals = subset[percentiles].values[0]
                plt.plot(x_labels, y_vals, marker='o', label=backend)
                
        plt.title("Latency percentiles at intensity=60 req/s (cardinality=low)")
        plt.xlabel("Percentile")
        plt.ylabel("Latency, ms")
        plt.legend()
        plt.grid(True)
        plt.savefig(out / "percentile_curves.png", dpi=120)
        print("Saved plot:", out / "percentile_curves.png")
        
    except Exception as e:
        print("Plot skipped:", e)

if __name__ == "__main__":
    main()