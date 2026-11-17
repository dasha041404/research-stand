import os
import random
import time
from fastapi import FastAPI, Response
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Volunteer Platform SUT")

# Поведенческие метрики (социальная активность)
student_action_total = Counter(
    "student_action_total",
    "Total student actions",
    ["action_type", "cluster"],
)

# Технические метрики
active_sessions = Gauge("active_sessions", "Number of active sessions")

ACTION_TYPES = ["event_signup", "application_submit", "review_post",
                "achievement_received", "friend_invited"]
CLUSTERS = [f"cluster_{i}" for i in range(1, 6)]  # 5 кластеров

Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/action/{action_type}")
def do_action(action_type: str):
    if action_type not in ACTION_TYPES:
        return {"error": "unknown action"}, 400
    cluster = random.choice(CLUSTERS)
    student_action_total.labels(action_type=action_type, cluster=cluster).inc()
    # имитация обработки
    time.sleep(random.uniform(0.001, 0.005))
    return {"status": "ok", "action": action_type, "cluster": cluster}


@app.post("/cardinality/{level}")
def set_cardinality(level: str):
    """
    Управление кардинальностью: low = 5 action_types × 5 clusters = 25 рядов,
    high = 5 action_types × 400 students = 2000+ рядов.
    Для простоты high достигается через эмуляцию: генерируем много серий
    через labels student_id.
    """
    if level == "high":
        for action in ACTION_TYPES:
            for i in range(400):
                student_action_total.labels(action_type=action, cluster=f"student_{i}").inc(0)
    return {"cardinality": level}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)