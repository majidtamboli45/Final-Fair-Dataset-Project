print("🔥 APP STARTING...")
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pandas as pd
import io
import datetime
import jwt
from functools import wraps

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

from fairlearn.metrics import demographic_parity_difference
from fairlearn.reductions import ExponentiatedGradient, DemographicParity

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

SECRET_KEY = "fairai_secret_key"

# =============================
# 🔐 LOGIN SYSTEM
# =============================
fake_user = {"username": "admin", "password": "1234"}

@app.route('/')
def home():
    return "🚀 FairAI Backend Running Successfully!"

@app.route('/login', methods=['POST'])
def login():
    data = request.json

    if data["username"] == fake_user["username"] and data["password"] == fake_user["password"]:
        token = jwt.encode({
            "user": data["username"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        }, SECRET_KEY, algorithm="HS256")

        return jsonify({"status": "success", "token": token})

    return jsonify({"status": "fail"}), 401


# =============================
# 🔐 AUTH DECORATOR
# =============================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "Token missing"}), 401

        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)

    return decorated


# =============================
# 🔍 INSPECT DATASET
# =============================
@app.route('/inspect', methods=['POST'])
@token_required
def inspect():
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({"error": "No file uploaded"})

        df = pd.read_csv(file)

        columns = list(df.columns)
        target_candidates = [col for col in columns if df[col].nunique() == 2]
        sensitive_candidates = [col for col in columns if df[col].nunique() <= 5]

        warnings = []

        if df.isnull().sum().sum() > 0:
            warnings.append("⚠ Dataset contains missing values")

        if not target_candidates:
            warnings.append("❌ No binary target column found")

        if not sensitive_candidates:
            warnings.append("⚠ No suitable sensitive feature found")

        return jsonify({
            "columns": columns,
            "target_candidates": target_candidates,
            "sensitive_candidates": sensitive_candidates,
            "warnings": warnings
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# =============================
# 📊 ANALYZE MODEL (UNCHANGED)
# =============================
@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        file = request.files.get('file')
        target = request.form.get("target")
        sensitive = request.form.get("sensitive")

        if not file or not target or not sensitive:
            return jsonify({"error": "Missing inputs"})

        # ✅ Read uploaded file (NOT local file)
        df = pd.read_csv(file)

        if target not in df.columns:
            return jsonify({"error": "Invalid target column"})

        if sensitive not in df.columns:
            return jsonify({"error": "Invalid sensitive column"})

        if df[target].nunique() != 2:
            return jsonify({"error": "Target must be binary"})

        X = pd.get_dummies(df.drop(target, axis=1))
        y = df[target]
        s = df[sensitive]

        X_train, X_test, y_train, y_test, s_train, s_test = train_test_split(
            X, y, s, test_size=0.3, random_state=42
        )

        model = LogisticRegression(max_iter=300)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)

        bias = demographic_parity_difference(
            y_true=y_test,
            y_pred=y_pred,
            sensitive_features=s_test
        )

        fairness = round(100 - abs(bias * 100), 2)

        # Column-wise bias
        column_bias = {}
        for col in df.columns:
            if col == target:
                continue
            try:
                if df[col].nunique() <= 10:
                    group_means = df.groupby(col)[target].mean()
                    diff = group_means.max() - group_means.min()
                    column_bias[col] = round(diff, 3)
            except:
                pass

        most_biased = max(column_bias, key=column_bias.get) if column_bias else None

        return jsonify({
            "fairness_score": fairness,
            "bias": round(bias, 3),
            "column_bias": column_bias,
            "most_biased_column": most_biased
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# =============================
# 🔥 FIX BIAS (FAIRLEARN ADDED)
# =============================
@app.route('/fix-bias', methods=['POST'])
@token_required
def fix_bias():
    try:
        file = request.files.get('file')
        target = request.form.get("target")
        sensitive = request.form.get("sensitive")

        df = pd.read_csv(file)

        # Fill missing
        df = df.fillna(df.median(numeric_only=True))

        X = pd.get_dummies(df.drop(target, axis=1))
        y = df[target]
        s = df[sensitive]

        X_train, X_test, y_train, y_test, s_train, s_test = train_test_split(
            X, y, s, test_size=0.3, random_state=42
        )

        base_model = LogisticRegression(max_iter=300)

        mitigator = ExponentiatedGradient(
            estimator=base_model,
            constraints=DemographicParity()
        )

        mitigator.fit(X_train, y_train, sensitive_features=s_train)

        y_pred = mitigator.predict(X_test)

        bias = demographic_parity_difference(
            y_true=y_test,
            y_pred=y_pred,
            sensitive_features=s_test
        )

        fairness = round(100 - abs(bias * 100), 2)

        return jsonify({
            "new_fairness_score": fairness,
            "new_bias": round(bias, 3),
            "fix": "Fairlearn Demographic Parity applied",
            "download_ready": True
        })

    except Exception as e:
        return jsonify({"error": str(e)})


# =============================
# 📥 DOWNLOAD FAIR DATASET (WEIGHTS)
# =============================
@app.route('/download-fair-data', methods=['POST'])
@token_required
def download_fair_data():
    try:
        file = request.files.get('file')
        target = request.form.get("target")
        sensitive = request.form.get("sensitive")

        df = pd.read_csv(file)
        df = df.fillna(df.median(numeric_only=True))

        group_counts = df.groupby([sensitive, target]).size().reset_index(name='count')
        total = len(df)

        def compute_weight(row):
            count = group_counts[
                (group_counts[sensitive] == row[sensitive]) &
                (group_counts[target] == row[target])
            ]['count'].values[0]
            return total / count

        df['fair_weight'] = df.apply(compute_weight, axis=1)

        buffer = io.BytesIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)

        return send_file(buffer, as_attachment=True,
                         download_name="fair_dataset_with_weights.csv",
                         mimetype='text/csv')

    except Exception as e:
        return jsonify({"error": str(e)})


# =============================
# 📄 PDF REPORT (UNCHANGED)
# =============================
@app.route('/generate-report', methods=['POST'])
@token_required
def generate_report():
    try:
        data = request.json

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer)
        styles = getSampleStyleSheet()

        content = [
            Paragraph("FairAI Report", styles['Title']),
            Spacer(1, 10),
            Paragraph(f"Fairness: {data['fairness']}", styles['Normal']),
            Paragraph(f"Bias: {data['bias']}", styles['Normal']),
        ]

        if data.get("fixed_fairness"):
            content.append(Spacer(1, 10))
            content.append(Paragraph("After Fix", styles['Heading2']))
            content.append(Paragraph(f"Fairness: {data['fixed_fairness']}", styles['Normal']))
            content.append(Paragraph(f"Bias: {data['fixed_bias']}", styles['Normal']))

        doc.build(content)
        buffer.seek(0)

        return send_file(buffer, as_attachment=True,
                         download_name="FairAI_Report.pdf",
                         mimetype='application/pdf')

    except Exception as e:
        return jsonify({"error": str(e)})


# =============================
# 🚀 RUN
# =============================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
