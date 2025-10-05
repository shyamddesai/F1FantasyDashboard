from flask import Flask, request
import json, pathlib

app = Flask(__name__)
COOKIE_FILE = "cookie.json"

@app.post("/cookies")
def drop():
    lines = request.data.decode().splitlines()
    wanted = {"consentUUID", "F1_FANTASY_007", "login-session", "reese84"}
    out = {k: v for k, v in (L.split("=", 1) for L in lines) if k in wanted}
    pathlib.Path(COOKIE_FILE).write_text(json.dumps({"Request Cookies": out}))
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)