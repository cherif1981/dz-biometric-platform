# Deployment Guide

## 🐳 Docker Deployment (Recommended)

### 1. Clone the repository
```bash
git clone https://github.com/cherif1981/dz-biometric-platform.git
cd dz-biometric-platform
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Start services
```bash
docker-compose up -d
```

Services:
- API: http://localhost:8000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 4. Run migrations
```bash
docker-compose exec api alembic upgrade head
```

## ☁️ Cloud Deployment

### Google Colab (Development)
```python
!pip install -r requirements.txt
!uvicorn src.main:app --host 0.0.0.0 --port 8000 &
```

### Cloudflare Tunnel (Public URL)
```bash
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared-linux-amd64
./cloudflared-linux-amd64 tunnel --url http://localhost:8000
```

## 🖥️ Production Setup

### Requirements
- Ubuntu 22.04+ / Debian 12+
- Python 3.10+
- PostgreSQL 15+
- Redis 7+
- NVIDIA GPU (optional, for faster inference)

### Steps
```bash
# 1. Install system dependencies
apt-get install -y python3-pip python3-venv libgl1 libglib2.0-0

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run with gunicorn + uvicorn workers
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Nginx Reverse Proxy
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 20M;
    }
}
```

## 🔧 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | change-me | JWT signing key |
| `DATABASE_URL` | sqlite:///... | Database connection |
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection |
| `FACE_MATCH_THRESHOLD` | 0.45 | Face similarity threshold |
| `LIVENESS_THRESHOLD` | 0.60 | Liveness detection threshold |
| `ANTISPOOF_THRESHOLD` | 0.55 | Anti-spoofing threshold |
| `ENVIRONMENT` | development | dev/staging/production |
| `DEBUG` | false | Enable debug mode |

## 📊 Monitoring

- **Prometheus** metrics: `/metrics` (if enabled)
- **Health check**: `/health`
- **Logs**: stdout (JSON format recommended)
