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

# Initialize Flask App
app = Flask(__name__)

# --- Configuration & Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
SCALER_PATH = os.path.join(BASE_DIR, "scaler.pkl")
# Path to test data (Go up one level from flask_app, then into data/processed)
TEST_DATA_PATH = os.path.join(BASE_DIR, "../data/processed/test.csv")

# --- Global Variables for Cache ---
model = None
scaler = None
model_metrics = {}


# --- Loading & Startup Calculations ---
def load_artifacts():
    global model, scaler, model_metrics
    print("⏳ Loading model and scaler...")
    try:
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        print("✅ Artifacts loaded successfully.")

        # Calculate Metrics Once at Startup
        if os.path.exists(TEST_DATA_PATH):
            print("⏳ Calculating model performance metrics...")
            test_df = pd.read_csv(TEST_DATA_PATH)
            X_test = test_df.drop("cardio", axis=1)
            y_test = test_df["cardio"]

            y_pred = model.predict(X_test)
            y_prob = model.predict_proba(X_test)[:, 1]

            # Metrics
            cm = confusion_matrix(y_test, y_pred)
            fpr, tpr, _ = roc_curve(y_test, y_prob)

            # Downsample ROC curve for web display (keep 50 points to stay fast)
            indices = np.linspace(0, len(fpr) - 1, 50, dtype=int)

            model_metrics = {
                "accuracy": round(accuracy_score(y_test, y_pred) * 100, 2),
                "precision": round(precision_score(y_test, y_pred) * 100, 2),
                "recall": round(recall_score(y_test, y_pred) * 100, 2),
                "f1": round(f1_score(y_test, y_pred) * 100, 2),
                "cm": cm.tolist(),  # Convert to list for JSON serialization
                "roc_fpr": fpr[indices].tolist(),
                "roc_tpr": tpr[indices].tolist(),
            }
            print("✅ Metrics calculated.")
        else:
            print("⚠️ Warning: test.csv not found. Model dashboard will be empty.")

    except Exception as e:
        print(f"❌ Error during startup: {e}")


# Load immediately
load_artifacts()


# --- Validation Logic ---
def validate_input(data):
    errors = []

    # 1. Age (Years)
    age = int(data.get("age", 0))
    if age < 10 or age > 120:
        errors.append("Age must be between 10 and 120.")

    # 2. Height (cm)
    height = float(data.get("height", 0))
    if height < 50 or height > 250:
        errors.append("Height must be between 50cm and 250cm.")

    # 3. Weight (kg)
    weight = float(data.get("weight", 0))
    if weight < 10 or weight > 300:
        errors.append("Weight must be between 10kg and 300kg.")

    # 4. Blood Pressure
    ap_hi = float(data.get("ap_hi", 0))
    ap_lo = float(data.get("ap_lo", 0))

    if ap_hi < 50 or ap_hi > 250:
        errors.append("Systolic BP (High) must be between 50 and 250.")
    if ap_lo < 30 or ap_lo > 200:
        errors.append("Diastolic BP (Low) must be between 30 and 200.")
    if ap_lo >= ap_hi:
        errors.append("Diastolic BP cannot be higher than Systolic BP.")

    return errors


# --- Preprocessing Function ---
def preprocess_input(data):
    # Extract & Convert
    age = int(data["age"])
    gender = int(data["gender"])
    height = float(data["height"])
    weight = float(data["weight"])
    ap_hi = float(data["ap_hi"])
    ap_lo = float(data["ap_lo"])
    smoke = int(data["smoke"])
    alco = int(data["alco"])
    active = int(data["active"])
    chol = int(data["cholesterol"])
    gluc = int(data["gluc"])

    # Feature Engineering: BMI
    bmi = weight / ((height / 100) ** 2)

    # One-Hot Encoding
    chol_1 = 1 if chol == 1 else 0
    chol_2 = 1 if chol == 2 else 0
    chol_3 = 1 if chol == 3 else 0

    gluc_1 = 1 if gluc == 1 else 0
    gluc_2 = 1 if gluc == 2 else 0
    gluc_3 = 1 if gluc == 3 else 0

    # Scale Numericals
    nums = pd.DataFrame(
        [[age, height, weight, ap_hi, ap_lo, bmi]],
        columns=["age_years", "height", "weight", "ap_hi", "ap_lo", "bmi"],
    )
    nums_scaled = scaler.transform(nums)

    # Assemble
    final_features = np.array(
        [
            nums_scaled[0][0],
            gender,
            nums_scaled[0][1],
            nums_scaled[0][2],
            nums_scaled[0][3],
            nums_scaled[0][4],
            smoke,
            alco,
            active,
            nums_scaled[0][5],
            chol_1,
            chol_2,
            chol_3,
            gluc_1,
            gluc_2,
            gluc_3,
        ]
    ).reshape(1, -1)

    return final_features, bmi


# --- Routes ---


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/model")
def model_page():
    return render_template("model.html", metrics=model_metrics)


@app.route("/predict", methods=["POST"])
def predict():
    if not model or not scaler:
        return render_template(
            "index.html", error="Model not loaded. Check server logs."
        )

    # Get data
    data = request.form

    # 1. Validate Input (Impossible Values)
    validation_errors = validate_input(data)
    if validation_errors:
        return render_template(
            "index.html",
            validation_errors=validation_errors,
            inputs=data,
            scroll_to_result=True,
        )

    try:
        # 2. Preprocess & Predict
        features, bmi_val = preprocess_input(data)
        prediction = model.predict(features)[0]
        probability = model.predict_proba(features)[0][1]

        # 3. Prepare Result
        risk_percentage = round(probability * 100, 2)
        risk_level = "High" if risk_percentage > 50 else "Low"
        alert_class = "danger" if risk_percentage > 50 else "success"

        chart_data = {
            "user_bmi": round(bmi_val, 2),
            "avg_healthy_bmi": 23.5,
            "avg_sick_bmi": 29.8,
            "user_bp": int(data["ap_hi"]),
            "avg_healthy_bp": 120,
            "avg_sick_bp": 145,
        }

        return render_template(
            "index.html",
            prediction_text=f"{risk_percentage}%",
            risk_level=risk_level,
            alert_class=alert_class,
            scroll_to_result=True,
            chart_data=chart_data,
            inputs=data,
        )

    except Exception as e:
        return render_template(
            "index.html", error=f"Prediction Error: {str(e)}", inputs=data
        )


if __name__ == "__main__":
    app.run(debug=True)
