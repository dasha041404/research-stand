"""
Оркестратор прогонов. Запускает Locust против SUT, сохраняет CSV и манифест.
Windows 11 + Docker Desktop: запускать из PowerShell.
"""
import argparse
import itertools
import json
import os
import platform
import random
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def sh(*args, env=None, check=True):
    return subprocess.run(
        args, check=check, capture_output=True, text=True,
        env={**os.environ, **(env or {})}
    ).stdout.strip()


def manifest(run_id, params, rep, cfg):
    try:
        git_commit = sh("git", "rev-parse", "HEAD")
        git_dirty = bool(sh("git", "status", "--porcelain"))
    except Exception:
        git_commit, git_dirty = "unknown", None

    try:
        images = sh("docker", "compose", "images", "--format", "json")
    except Exception:
        images = "{}"

    return {
        "run_id": run_id,
        "params": params,
        "repetition": rep,
        "seed": cfg["seed"],
        "git_commit": git_commit,
        "git_dirty": git_dirty,
        "images": images,
        "host": {
            "os": platform.platform(),
            "cpu_count": os.cpu_count(),
            "machine": platform.machine(),
        },
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def locust(users, seconds, prefix):
    subprocess.run(
        ["docker", "compose", "--profile", "run", "run", "--rm", "load",
         "-f", "/mnt/locust/locustfile.py", "--headless",
         "-u", str(users), "-r", str(users), "-t", f"{seconds}s",
         "--host", "http://app:8000", "--csv", f"/results/{prefix}"],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--backend", default="both", choices=["prometheus", "victoriametrics", "both"])
    args = parser.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())

    backends = cfg["factors"]["backend"]
    if args.backend != "both":
        backends = [args.backend]

    # Полный план: backend × intensity × cardinality × repetitions
    plan = []
    for combo in itertools.product(backends,
                                   cfg["factors"]["intensity"],
                                   cfg["factors"]["cardinality"]):
        backend, intensity, cardinality = combo
        for r in range(cfg["repetitions"]):
            plan.append({"backend": backend, "intensity": intensity,
                         "cardinality": cardinality, "rep": r})

    if cfg.get("randomize_order"):
        random.Random(cfg["seed"]).shuffle(plan)

    out = ROOT / "results" / "raw"
    out.mkdir(parents=True, exist_ok=True)

    # Поднимаем SUT и БД один раз
    sh("docker", "compose", "up", "-d", "app", "db", "cadvisor", "grafana")

    for i, p in enumerate(plan, 1):
        backend = p["backend"]
        # Останавливаем оба backend, поднимаем нужный
        sh("docker", "compose", "stop", "prometheus", "victoriametrics", check=False)
        sh("docker", "compose", "up", "-d", backend)

        # Очистка хранилища backend между прогонами
        if backend == "prometheus":
            sh("docker", "compose", "exec", "-T", "prometheus",
               "rm", "-rf", "/prometheus/data", check=False)
        # (для VM — аналогично, если нужно)

        time.sleep(5)  # дождаться старта

        # Устанавливаем кардинальность
        subprocess.run(
            ["docker", "compose", "exec", "-T", "app",
             "python", "-c", 
             f"import urllib.request; urllib.request.urlopen(urllib.request.Request('http://localhost:8000/cardinality/{p['cardinality']}', method='POST'))"],
            check=False,
        )

        run_id = f"{backend}_{p['intensity']}_{p['cardinality']}_r{p['rep']}_{uuid.uuid4().hex[:6]}"
        print(f"[{i}/{len(plan)}] {run_id}")

        # Warm-up (не идёт в анализ)
        locust(p["intensity"], cfg["warmup_seconds"], f"warmup_{run_id}")
        # Основной прогон
        locust(p["intensity"], cfg["duration_seconds"], run_id)

        params = {k: v for k, v in p.items() if k != "rep"}
        (out / f"{run_id}.json").write_text(
            json.dumps(manifest(run_id, params, p["rep"], cfg), indent=2, ensure_ascii=False)
        )

    print("Done. Raw results in results/raw/")


if __name__ == "__main__":
    main()