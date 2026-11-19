import os
import random
from locust import HttpUser, task, constant_pacing

# Скрипт будет искать переменную окружения LOCUST_WAIT_TIME.
# Если она задана (например, "0.016" для 60 RPS), он использует её.
# Если нет (например, при ручном запуске), по умолчанию ставит 0.1 (10 RPS).
PACING = float(os.getenv("LOCUST_WAIT_TIME", 0.1))

ACTION_TYPES = ["event_signup", "application_submit", "review_post",
                "achievement_received", "friend_invited"]

class StudentUser(HttpUser):
    # Задаем время ожидания между запросами
    wait_time = constant_pacing(PACING)

    @task(5)
    def do_action(self):
        action = random.choice(ACTION_TYPES)
        self.client.post(f"/action/{action}", name="/action/[type]")

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")