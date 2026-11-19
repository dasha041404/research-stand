import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

df = pd.read_csv("results/processed/runs.csv")
out = Path("results/processed")

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# --- Левый график (10 req/s) ---
sns.boxplot(data=df[df["intensity"] == 10], x="backend", y="p95", hue="cardinality", ax=axes[0], palette="Set2", width=0.6)
sns.stripplot(data=df[df["intensity"] == 10], x="backend", y="p95", hue="cardinality", ax=axes[0], dodge=True, jitter=True, size=7, alpha=0.8, palette="dark")
axes[0].set_title("Intensity: 10 req/s")
axes[0].set_ylabel("p95 latency, ms")
axes[0].set_ylim(0, 50)
axes[0].set_xlabel("")
# Настройка легенды
handles, labels = axes[0].get_legend_handles_labels()
axes[0].legend(handles[:2], ["high (cardinality)", "low (cardinality)"], title="Cardinality", loc="upper right")

# --- Правый график (60 req/s) ---
sns.boxplot(data=df[df["intensity"] == 60], x="backend", y="p95", hue="cardinality", ax=axes[1], palette="Set2", width=0.6)
sns.stripplot(data=df[df["intensity"] == 60], x="backend", y="p95", hue="cardinality", ax=axes[1], dodge=True, jitter=True, size=7, alpha=0.8, palette="dark")
axes[1].set_title("Intensity: 60 req/s")
axes[1].set_ylabel("p95 latency, ms")
axes[1].set_ylim(185, 205)  # Более точный масштаб для 60 req/s
axes[1].set_xlabel("")
# Настройка легенды
handles, labels = axes[1].get_legend_handles_labels()
axes[1].legend(handles[:2], ["high (cardinality)", "low (cardinality)"], title="Cardinality", loc="upper right")

plt.suptitle("p95 latency by backend and cardinality (grouped by intensity)", fontsize=14)
plt.tight_layout()
plt.savefig(out / "p95_boxplot_clear.png", dpi=150)
print("График сохранен:", out / "p95_boxplot_clear.png")