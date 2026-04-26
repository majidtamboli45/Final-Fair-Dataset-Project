from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import os

app = Flask(__name__)
CORS(app)

# ================= LOGIN =================
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    if data.get("username") == "admin" and data.get("password") == "1234":
        return jsonify({"token": "fake-jwt-token"})

    return jsonify({"error": "Invalid credentials"}), 401


# ================= INSPECT =================
@app.route("/inspect", methods=["POST"])
def inspect():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    try:
        df = pd.read_csv(file)

        # 🔥 Example processing (you can improve this)
        df["processed"] = True

        output_path = "fixed_dataset.csv"
        df.to_csv(output_path, index=False)

        return jsonify({
            "message": "Dataset processed successfully",
            "rows": len(df),
            "columns": list(df.columns)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================= DOWNLOAD =================
@app.route("/download", methods=["GET"])
def download():
    file_path = "fixed_dataset.csv"

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    return send_file(
        file_path,
        as_attachment=True,
        download_name="fixed_dataset.csv"
    )


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
