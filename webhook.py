from flask import Flask, request, jsonify
import json

app = Flask(__name__)
COOKIE_FILE = "cookie.json"

@app.route("/cookies", methods=["POST"])
def cookies():
    try:
        data = request.get_json(force=True)
        # print("Received JSON data:", data)
        
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return jsonify({"status": "success"}), 200
    except Exception as e:
        print("Error processing JSON:", e)
        print(f"Raw payload: {request.data}")
        return jsonify({"status": "error", "message": str(e)}), 400
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)