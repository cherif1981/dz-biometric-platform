# Security Policy

## 🛡️ Security Measures

### Authentication & Authorization
- **JWT tokens** for API authentication (HS256)
- **Access + Refresh tokens** with configurable expiry
- **Scope-based permissions** (`RequireScopes` dependency)
- **Bcrypt** password hashing (via `passlib`)

### Data Protection
- **Field-level encryption** using Fernet (symmetric)
- **AES-256** for sensitive fields (NIN, birth date)
- **HTTPS only** in production
- **Environment variables** for secrets (never hardcoded)

### Biometric Data
- Face embeddings are **not stored** by default
- Original images can be discarded after verification
- Audit logs contain **metadata only** (no raw biometrics)

### Anti-Spoofing
- **MiniFASNetV2** for presentation attack detection
- **Liveness detection** (passive + challenge-response)
- **Heuristic fallback** when ML models unavailable

### Audit Trail
- Every verification attempt is logged
- Records include: timestamp, status, scores, client IP
- Logs stored in PostgreSQL (production) or SQLite (dev)

## 🔐 Best Practices

1. **Rotate secrets** regularly (SECRET_KEY, JWT keys)
2. **Use HTTPS** in all production deployments
3. **Restrict CORS** to trusted origins
4. **Rate limit** API endpoints (use nginx or Cloudflare)
5. **Monitor** audit logs for anomalies
6. **Update** dependencies regularly (`pip-audit`)

## ⚠️ Reporting Vulnerabilities

If you discover a security vulnerability, please email:
**meddourcherif1981@gmail.com**

Do NOT open a public GitHub issue for security issues.
