"""Locust load test for /api/v1/auth/login + /health."""
from locust import HttpUser, task, between


class AuthUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.username = "testuser"
        self.password = "SecurePass123!"

    @task(3)
    def login(self):
        with self.client.post(
            "/api/v1/auth/login",
            data={"username": self.username, "password": self.password},
            catch_response=True,
        ) as r:
            if r.status_code in (200, 401):
                r.success()
            else:
                r.failure(f"unexpected {r.status_code}")

    @task(1)
    def health(self):
        self.client.get("/health")
