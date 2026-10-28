"""تشغيل المراقب كعملية مستقلة مع تنبيهات خارجية."""
import os, sys, json, time, signal, smtplib, urllib.request
from email.message import EmailMessage
import monitor

DB = os.environ.get("AUDIT_DB", "/tmp/audit.db")
INTERVAL = int(os.environ.get("MONITOR_INTERVAL", "10"))

def alert_webhook(info: dict):
    """أرسل إلى Slack/Discord/webhook — القناة الخارجية."""
    url = os.environ.get("ALERT_WEBHOOK_URL")
    if not url:
        print(f"[ALERT] {json.dumps(info)}", flush=True); return
    body = json.dumps({"text": f"🚨 AUDIT TAMPER: {info}"}).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=5)
        print("[ALERT] sent to webhook", flush=True)
    except Exception as e:
        print(f"[ALERT-FALLBACK] webhook failed: {e}; info={info}", flush=True)

def alert_email(info: dict):
    """احتياطي عبر البريد. يتطلب SMTP_HOST/SMTP_USER/SMTP_PASS/ALERT_EMAIL."""
    host = os.environ.get("SMTP_HOST")
    if not host: return
    msg = EmailMessage()
    msg["Subject"] = "🚨 AUDIT CHAIN TAMPERED"
    msg["From"] = os.environ.get("SMTP_USER", "audit@localhost")
    msg["To"] = os.environ.get("ALERT_EMAIL", "")
    msg.set_content(json.dumps(info, indent=2))
    with smtplib.SMTP_SSL(host, 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)

def on_tamper(info):
    alert_webhook(info)
    try: alert_email(info)
    except Exception as e: print(f"email alert failed: {e}", flush=True)
    sys.exit(2)   # exit code مميز — يلتقطه systemd/monitoring

def on_check(info):
    print(f"[ok] records={info['records']} head={info['head'][:12]}…", flush=True)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *a: sys.exit(0))
    monitor.monitor(DB, interval=INTERVAL,
                    on_tamper=on_tamper, on_check=on_check)
