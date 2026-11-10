
from locust import HttpUser, task, between
import os

SELFIE = open("tests/data/selfie_sample.jpg", "rb").read()
DOC    = open("tests/data/cnibe_sample.jpg", "rb").read()

class KYCUser(HttpUser):
    wait_time = between(2, 5)

    def on_start(self):
        r = self.client.post(
            "/api/v1/auth/token",
            json={"username": "loadtest", "password": os.getenv("LOAD_PASS", "x")},
            name="/auth/token",
        )
        if r.status_code == 200:
            self.token = r.json().get("access_token", "")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = ""
            self.headers = {}

    @task(3)
    def verify_full(self):
        with self.client.post(
            "/api/v1/verify",
            files={
                "selfie":   ("selfie.jpg", SELFIE, "image/jpeg"),
                "document": ("doc.jpg",    DOC,    "image/jpeg"),
            },
            headers=self.headers,
            name="/verify",
            catch_response=True,
        ) as r:
            if r.status_code == 429:
                r.failure("429 rate limited")
            elif r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
            else:
                body = r.json()
                if body.get("decision") not in ("REVIEW", "REJECT"):
                    r.failure(f"unexpected decision={body.get('decision')}")

    @task(1)
    def liveness_only(self):
        with self.client.post(
            "/api/v1/liveness",
            files={"image": ("s.jpg", SELFIE, "image/jpeg")},
            headers=self.headers,
            name="/liveness",
            catch_response=True,
        ) as r:
            if r.status_code != 200:
                r.failure(f"HTTP {r.status_code}")
