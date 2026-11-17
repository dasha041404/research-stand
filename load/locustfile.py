import random
from locust import HttpUser, task, constant

ACTION_TYPES = ["event_signup", "application_submit", "review_post",
                "achievement_received", "friend_invited"]

class StudentUser(HttpUser):
    wait_time = constant(0)  # замкнутая модель: максимальная интенсивность

    @task(5)
    def do_action(self):
        action = random.choice(ACTION_TYPES)
        self.client.post(f"/action/{action}", name="/action/[type]")

    @task(1)
    def health(self):
        self.client.get("/health", name="/health")