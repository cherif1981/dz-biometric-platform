# Load Testing (k6)

## Install

```bash
brew install k6        # macOS
sudo apt install k6    # Debian/Ubuntu
```

## Smoke (no token, expects 401)

```bash
k6 run -e BASE_URL=http://localhost:8000 deploy/k6/verify_load.js
```

## Full (JWT + fixtures)

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d 'username=demo&password=demo' | jq -r .access_token)

k6 run \
  -e BASE_URL=http://localhost:8000 \
  -e TOKEN="$TOKEN" \
  -e ID_IMAGE=fixtures/id.jpg \
  -e SELFIE=fixtures/selfie.jpg \
  deploy/k6/verify_load.js
```

## Thresholds

- `http_req_failed < 5%`
- `p95 < 1500 ms`, `p99 < 3000 ms`
- No 5xx responses
