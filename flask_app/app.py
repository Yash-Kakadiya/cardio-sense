import numpy as np
import pandas as pd
from flask import Flask, request, render_template, jsonify
import joblib
import os
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_curve,
)

app = Flask(__name__)

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")
FEATURE_PATH = os.path.join(BASE_DIR, "features.pkl")
TEST_DATA_PATH = os.path.join(BASE_DIR, "../data/processed/test.csv")

# --- Globals ---
model = None
scaler = None
feature_names = []
model_metrics = {}


def load_artifacts():
    global model, scaler, feature_names, model_metrics
    try:
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        feature_names = joblib.load(FEATURE_PATH)
        print("✅ Artifacts Loaded")

        if os.path.exists(TEST_DATA_PATH):
            test_df = pd.read_csv(TEST_DATA_PATH)
            X_base = test_df.drop("cardio", axis=1).values
            y_test = test_df["cardio"]

            # Pulse Pressure Engineering
            pulse_pressure = X_base[:, 4] - X_base[:, 5]
            X_final = np.hstack((X_base, pulse_pressure.reshape(-1, 1)))

            # Predictions
            y_pred = model.predict(X_final)
            y_prob = model.predict_proba(X_final)[:, 1]

            # 1. Confusion Matrix
            cm = confusion_matrix(y_test, y_pred)

            # 2. ROC Curve
            fpr, tpr, _ = roc_curve(y_test, y_prob)
            if len(fpr) > 500:
                indices = np.linspace(0, len(fpr) - 1, 500, dtype=int)
                fpr = fpr[indices]
                tpr = tpr[indices]

            # 3. Feature Importance (Fix for VotingClassifier)
            # VotingClassifier doesn't have feature_importances_, so we grab it from the internal Random Forest ('rf')
            if hasattr(model, "feature_importances_"):
                importances = model.feature_importances_
            elif hasattr(model, "named_estimators_"):
                # Extract from the Random Forest sub-model
                importances = model.named_estimators_["rf"].feature_importances_
            else:
                # Fallback if no importance available
                importances = np.zeros(len(feature_names))

            sorted_idx = np.argsort(importances)[::-1]
            top_n = 10

            # 4. Confidence Distribution
            hist, _ = np.histogram(y_prob, bins=10, range=(0, 1))

            model_metrics = {
                "accuracy": round(accuracy_score(y_test, y_pred) * 100, 2),
                "precision": round(precision_score(y_test, y_pred) * 100, 2),
                "recall": round(recall_score(y_test, y_pred) * 100, 2),
                "f1": round(f1_score(y_test, y_pred) * 100, 2),
                "cm": cm.tolist(),
                "roc_fpr": fpr.tolist(),
                "roc_tpr": tpr.tolist(),
                "feat_names": [feature_names[i] for i in sorted_idx[:top_n]],
                "feat_scores": [round(importances[i], 4) for i in sorted_idx[:top_n]],
                "conf_hist": hist.tolist(),
                "class_dist": [int(np.sum(y_test == 0)), int(np.sum(y_test == 1))],
            }
            print("✅ Metrics Calculated")
    except Exception as e:
        print(f"❌ Error: {e}")


load_artifacts()


def validate_input(data):
    errors = []
    try:
        # Range Checks
        if not (10 <= int(data["age"]) <= 120):
            errors.append("Age must be between 10 and 120.")
        if not (50 <= float(data["height"]) <= 250):
            errors.append("Height must be realistic (50-250cm).")
        if not (30 <= float(data["weight"]) <= 250):
            errors.append("Weight must be realistic (30-250kg).")

        # Medical Logic Checks
        sys = float(data["ap_hi"])
        dia = float(data["ap_lo"])

        if sys > 250 or sys < 60:
            errors.append("Systolic BP is out of medical range (60-250).")
        if dia > 180 or dia < 30:
            errors.append("Diastolic BP is out of medical range (30-180).")
        if dia >= sys:
            errors.append("Diastolic BP cannot be higher than or equal to Systolic BP.")
        if (sys - dia) < 10:
            errors.append("Pulse Pressure is dangerously low (Difference < 10).")

    except ValueError:
        errors.append("Please ensure all fields contain valid numbers.")
    return errors


def preprocess_input(data):
    # Extract
    age = int(data["age"])
    gender = int(data["gender"])
    h = float(data["height"])
    w = float(data["weight"])
    sys = float(data["ap_hi"])
    dia = float(data["ap_lo"])

    # Calc BMI
    bmi = w / ((h / 100) ** 2)

    # Scale Inputs (Must match training scaler order)
    nums = pd.DataFrame(
        [[age, h, w, sys, dia, bmi]],
        columns=["age_years", "height", "weight", "ap_hi", "ap_lo", "bmi"],
    )
    nums_s = scaler.transform(nums)[0]

    # Calc Pulse Pressure (Scaled)
    pp_scaled = nums_s[3] - nums_s[4]

    # Assemble Vector
    # Order: age, gender, height, weight, ap_hi, ap_lo, smoke, alco, active, bmi,
    #        chol_1, chol_2, chol_3, gluc_1, gluc_2, gluc_3, pulse_pressure
    features = np.array(
        [
            nums_s[0],
            gender,
            nums_s[1],
            nums_s[2],
            nums_s[3],
            nums_s[4],
            int(data["smoke"]),
            int(data["alco"]),
            int(data["active"]),
            nums_s[5],
            1 if data["cholesterol"] == "1" else 0,
            1 if data["cholesterol"] == "2" else 0,
            1 if data["cholesterol"] == "3" else 0,
            1 if data["gluc"] == "1" else 0,
            1 if data["gluc"] == "2" else 0,
            1 if data["gluc"] == "3" else 0,
            pp_scaled,
        ]
    ).reshape(1, -1)

    return features, bmi


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/model")
def model_page():
    return render_template("model.html", metrics=model_metrics)


@app.route("/predict", methods=["POST"])
def predict():
    if not model:
        return render_template("index.html", error="Model failed to load.")

    data = request.form
    errors = validate_input(data)
    if errors:
        return render_template("index.html", validation_errors=errors, inputs=data)

    try:
        features, bmi = preprocess_input(data)
        prob = model.predict_proba(features)[0][1]

        # Chart Data
        chart = {
            "user_bmi": round(bmi, 1),
            "user_bp": int(data["ap_hi"]),
            "user_pp": int(data["ap_hi"]) - int(data["ap_lo"]),
        }

        return render_template(
            "index.html",
            prediction_text=f"{round(prob*100, 1)}%",
            risk_level="High" if prob > 0.5 else "Low",
            alert_class="danger" if prob > 0.5 else "success",
            chart_data=chart,
            inputs=data,
        )
    except Exception as e:
        return render_template("index.html", error=str(e), inputs=data)


if __name__ == "__main__":
    app.run(debug=True)
