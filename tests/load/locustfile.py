from locust import HttpUser, task, between
import random

class BiometricUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(5)
    def health(self):
        self.client.get("/health")

    @task(3)
    def verify(self):
        self.client.post("/verify", json={
            "subject_id": f"user-{random.randint(1, 10000)}",
            "face_score": random.uniform(0.3, 0.99),
            "liveness_score": random.uniform(0.3, 0.99),
            "antispoofing_score": random.uniform(0.3, 0.99),
        })

    @task(1)
    def metrics(self):
        self.client.get("/metrics")
