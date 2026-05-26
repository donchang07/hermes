import os, sys
import requests

token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
chat  = os.environ.get("TELEGRAM_CHAT_ID", "")
text  = os.environ.get("MSG", "")

if not text.strip():
    print("KRX closed today - skipping")
    sys.exit(0)

if not token or not chat:
    print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
    sys.exit(1)

r = requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    json={"chat_id": chat, "text": text},
    timeout=10
)
print("Telegram response:", r.status_code)
if r.status_code != 200:
    print(r.text)
    sys.exit(1)
