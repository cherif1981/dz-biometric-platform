# PAD Evaluation Report

## Load test

**Target:** mock KYC backend (synthetic latency, no real models)
**Purpose:** validate locust harness + CSV parser before staging run
**Date:** 2026-11-10T15:50:27.091543+00:00

| Scenario | Users | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Errors |
|----------|-------|-----|----------|----------|----------|--------|
| smoke | 10 | 2.1 | 2200 | 3700 | 4000 | 0 |
| baseline | 50 | 9.0 | 2200 | 3900 | 4000 | 0 |
| target_load | 100 | 18.0 | 2200 | 3800 | 4000 | 0 |

**Interpretation:**
- RPS scales linearly with users (2.1 → 9.0 → 18.0) — backend not saturated
- Zero failures across 1,647 requests
- p50/p99 reflect synthetic latency bounds, NOT real model inference

**SLO:** p95 <= 8,000 ms, error rate < 0.5%

**Verdict:** Harness validated. Production SLO must be measured on
staging with real PAD + OCR + face match. Expected p95 on staging:
6,000-8,000 ms.

### Reproduce

Install: `pip install locust`

Start mock backend: `python3 /tmp/mock_kyc.py &`

Run: `locust -f tests/load/locustfile.py --host http://127.0.0.1:18090 --users 100 --spawn-rate 10 --run-time 60s --headless`
