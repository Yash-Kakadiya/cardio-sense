import numpy as np
import pandas as pd
from flask import Flask, request, render_template, jsonify, session, redirect, url_for
import joblib
import os
import shap
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_curve,
)

# --- Risk Threshold Configuration ---
RISK_THRESHOLDS = {
    "low": {
        "max": 0.35,
        "label": "Low",
        "class": "success",
        "icon": "check-circle",
        "color": "#10b981",
    },
    "moderate": {
        "max": 0.65,
        "label": "Moderate",
        "class": "warning",
        "icon": "exclamation-triangle",
        "color": "#f59e0b",
    },
    "high": {
        "max": 1.0,
        "label": "High",
        "class": "danger",
        "icon": "times-circle",
        "color": "#ef4444",
    },
}

app = Flask(__name__)
app.secret_key = "cardiosense_secret_key_2026"  # For session management

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
shap_explainer = None  # SHAP explainer for interpretability


def to_native_types(value):
    """Recursively convert NumPy values to JSON-safe native Python types."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [to_native_types(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {key: to_native_types(val) for key, val in value.items()}
    if isinstance(value, list):
        return [to_native_types(item) for item in value]
    if isinstance(value, tuple):
        return [to_native_types(item) for item in value]
    return value


def get_risk_category(probability):
    """Determine risk category based on probability thresholds."""
    if probability <= RISK_THRESHOLDS["low"]["max"]:
        return RISK_THRESHOLDS["low"]
    elif probability <= RISK_THRESHOLDS["moderate"]["max"]:
        return RISK_THRESHOLDS["moderate"]
    else:
        return RISK_THRESHOLDS["high"]


def load_artifacts():
    global model, scaler, feature_names, model_metrics, shap_explainer
    try:
        model = joblib.load(MODEL_PATH)
        scaler = joblib.load(SCALER_PATH)
        feature_names = joblib.load(FEATURE_PATH)
        print("✅ Artifacts Loaded")

        # Initialize SHAP Explainer
        # Use TreeExplainer for tree-based models (RF, XGB, GB in our VotingClassifier)
        try:
            # For VotingClassifier, we use the Random Forest estimator for SHAP
            if hasattr(model, "named_estimators_"):
                shap_explainer = shap.TreeExplainer(model.named_estimators_["rf"])
            else:
                shap_explainer = shap.TreeExplainer(model)
            print("✅ SHAP Explainer Initialized")
        except Exception as shap_err:
            print(f"⚠️ SHAP initialization failed: {shap_err}")
            shap_explainer = None

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

            model_metrics = to_native_types(
                {
                    "accuracy": round(accuracy_score(y_test, y_pred) * 100, 2),
                    "precision": round(precision_score(y_test, y_pred) * 100, 2),
                    "recall": round(recall_score(y_test, y_pred) * 100, 2),
                    "f1": round(f1_score(y_test, y_pred) * 100, 2),
                    "cm": cm.tolist(),
                    "roc_fpr": fpr.tolist(),
                    "roc_tpr": tpr.tolist(),
                    "feat_names": [feature_names[i] for i in sorted_idx[:top_n]],
                    "feat_scores": [
                        round(importances[i], 4) for i in sorted_idx[:top_n]
                    ],
                    "conf_hist": hist.tolist(),
                    "class_dist": [int(np.sum(y_test == 0)), int(np.sum(y_test == 1))],
                }
            )
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


def get_shap_explanation(features):
    """
    Generate SHAP-based explanation for a prediction.
    Returns top contributing factors (positive and negative).
    """
    if shap_explainer is None:
        return None

    try:
        shap_values = shap_explainer.shap_values(features)

        # ---- CASE 1: list output (older SHAP, binary clf) ----
        if isinstance(shap_values, list):
            shap_vals = shap_values[1][0]  # class 1, first sample

        # ---- CASE 2: ndarray output (your case) ----
        elif isinstance(shap_values, np.ndarray):
            # shape: (n_features, 2)
            if shap_values.ndim == 3:
                shap_vals = shap_values[0, :, 1]
            elif shap_values.ndim == 2:
                shap_vals = shap_values[:, 1]
            else:
                raise ValueError(f"Unexpected SHAP shape: {shap_values.shape}")

        # ---- CASE 3: new SHAP Explanation object ----
        elif hasattr(shap_values, "values"):
            shap_vals = shap_values.values[0]

        else:
            raise ValueError("Unknown SHAP output format")

        # ---- Feature names (NO pulse_pressure if model didn't see it) ----
        used_features = feature_names[: len(shap_vals)]

        contributions = []
        for name, val in zip(used_features, shap_vals):
            readable = (
                name.replace("_", " ")
                .replace("ap hi", "Systolic BP")
                .replace("ap lo", "Diastolic BP")
                .title()
            )

            contributions.append(
                {
                    "feature": readable,
                    "value": round(float(val), 4),
                    "impact": "increases" if val > 0 else "decreases",
                    "abs_value": abs(float(val)),
                }
            )

        contributions.sort(key=lambda x: x["abs_value"], reverse=True)

        return {
            "risk_factors": [c for c in contributions if c["value"] > 0][:5],
            "protective_factors": [c for c in contributions if c["value"] < 0][:3],
            "all_contributions": contributions[:10],
        }

    except Exception as e:
        import traceback

        print("SHAP ERROR:", e)
        traceback.print_exc()
        return None


FEATURE_EXPLANATIONS = {
    "Age Years": {
        "risk": "Increasing age naturally raises cardiovascular risk due to vascular changes.",
        "protective": "Your age contributes minimally to cardiovascular risk.",
    },
    "Systolic BP": {
        "risk": "Elevated systolic blood pressure puts extra strain on your heart and arteries.",
        "protective": "Healthy systolic blood pressure helps protect your heart.",
    },
    "Diastolic BP": {
        "risk": "High diastolic pressure indicates persistent arterial stress.",
        "protective": "Normal diastolic pressure supports good cardiovascular health.",
    },
    "BMI": {
        "risk": "Higher body weight increases cardiac workload and metabolic risk.",
        "protective": "A healthy body weight reduces strain on the heart.",
    },
    "Cholesterol 2": {
        "risk": "Borderline cholesterol levels can contribute to plaque buildup in arteries.",
        "protective": "Your cholesterol levels are not adding to your cardiovascular risk.",
    },
    "Cholesterol 3": {
        "risk": "High cholesterol significantly increases the risk of artery blockage.",
        "protective": "Healthy cholesterol levels help keep arteries clear.",
    },
    "Glucose 2": {
        "risk": "Elevated blood glucose may indicate insulin resistance.",
        "protective": "Normal glucose levels help protect blood vessels.",
    },
    "Glucose 3": {
        "risk": "High blood glucose is strongly linked to cardiovascular complications.",
        "protective": "Good glucose control lowers cardiovascular strain.",
    },
    "Smoking": {
        "risk": "Smoking damages blood vessels and reduces oxygen supply to the heart.",
        "protective": "Not smoking significantly reduces cardiovascular risk.",
    },
    "Alcohol": {
        "risk": "Regular alcohol intake can raise blood pressure and cardiac risk.",
        "protective": "Low alcohol consumption supports heart health.",
    },
    "Active": {
        "risk": "A sedentary lifestyle increases cardiovascular risk.",
        "protective": "Regular physical activity protects heart health.",
    },
}


def shap_strength(abs_value):
    if abs_value >= 0.06:
        return "significantly"
    elif abs_value >= 0.03:
        return "moderately"
    else:
        return "slightly"


def humanize_shap(contributions):
    explanations = []

    for c in contributions:
        feature = c["feature"]
        val = c["value"]
        abs_val = abs(val)

        direction = "risk" if val > 0 else "protective"
        strength = shap_strength(abs_val)

        template = FEATURE_EXPLANATIONS.get(feature)

        if template:
            sentence = template[direction]
        else:
            sentence = f"{feature} is {strength} affecting your cardiovascular risk."

        explanations.append(
            {
                "feature": feature,
                "message": sentence,
                "direction": "increase" if val > 0 else "decrease",
                "strength": strength,
                "impact": round(abs_val * 100, 1),
            }
        )

    return explanations


def summarize_explanations(human_explanations):
    if not human_explanations:
        return None

    top = human_explanations[0]
    return (
        f"Your cardiovascular risk is mainly influenced by {top['feature'].lower()}, "
        f"which is {top['strength']} increasing your risk. "
        "Addressing key lifestyle and clinical factors can help reduce this risk."
    )


def calculate_whatif_scenarios(data, current_prob, features):
    """
    Calculate how risk changes with lifestyle modifications.
    Returns scenarios showing potential risk reduction.
    """
    scenarios = []

    try:
        # Scenario 1: Weight Loss (if BMI > 25)
        h = float(data["height"])
        w = float(data["weight"])
        current_bmi = w / ((h / 100) ** 2)

        if current_bmi > 25:
            # Simulate 5kg weight loss
            new_weight = w - 5
            modified_data = data.copy()
            modified_data["weight"] = str(new_weight)
            new_features, new_bmi = preprocess_input(modified_data)
            new_prob = model.predict_proba(new_features)[0][1]
            change = (current_prob - new_prob) * 100

            if change > 0:
                scenarios.append(
                    {
                        "action": "Lose 5 kg",
                        "icon": "weight",
                        "current": f"BMI {current_bmi:.1f}",
                        "target": f"BMI {new_bmi:.1f}",
                        "risk_change": round(float(change), 1),
                        "new_risk": round(float(new_prob) * 100, 1),
                        "positive": True,
                    }
                )

        # Scenario 2: Blood Pressure Control (if sys > 130)
        sys = float(data["ap_hi"])
        dia = float(data["ap_lo"])

        if sys > 130:
            # Simulate BP reduction to 120/80
            modified_data = data.copy()
            modified_data["ap_hi"] = "120"
            modified_data["ap_lo"] = "80"
            new_features, _ = preprocess_input(modified_data)
            new_prob = model.predict_proba(new_features)[0][1]
            change = (current_prob - new_prob) * 100

            if change > 0:
                scenarios.append(
                    {
                        "action": "Control Blood Pressure",
                        "icon": "heartbeat",
                        "current": f"{int(sys)}/{int(dia)} mmHg",
                        "target": "120/80 mmHg",
                        "risk_change": round(float(change), 1),
                        "new_risk": round(float(new_prob) * 100, 1),
                        "positive": True,
                    }
                )

        # Scenario 3: Quit Smoking (if smoker)
        if data.get("smoke") == "1":
            modified_data = data.copy()
            modified_data["smoke"] = "0"
            new_features, _ = preprocess_input(modified_data)
            new_prob = model.predict_proba(new_features)[0][1]
            change = (current_prob - new_prob) * 100

            scenarios.append(
                {
                    "action": "Quit Smoking",
                    "icon": "smoking-ban",
                    "current": "Smoker",
                    "target": "Non-smoker",
                    "risk_change": round(float(change), 1),
                    "new_risk": round(float(new_prob) * 100, 1),
                    "positive": bool(change > 0),
                }
            )

        # Scenario 4: Reduce Alcohol (if drinker)
        if data.get("alco") == "1":
            modified_data = data.copy()
            modified_data["alco"] = "0"
            new_features, _ = preprocess_input(modified_data)
            new_prob = model.predict_proba(new_features)[0][1]
            change = (current_prob - new_prob) * 100

            scenarios.append(
                {
                    "action": "Reduce Alcohol",
                    "icon": "wine-glass-alt",
                    "current": "Regular drinker",
                    "target": "Minimal/No alcohol",
                    "risk_change": round(float(change), 1),
                    "new_risk": round(float(new_prob) * 100, 1),
                    "positive": bool(change > 0),
                }
            )

        # Scenario 5: Increase Physical Activity (if inactive)
        if data.get("active") == "0":
            modified_data = data.copy()
            modified_data["active"] = "1"
            new_features, _ = preprocess_input(modified_data)
            new_prob = model.predict_proba(new_features)[0][1]
            change = (current_prob - new_prob) * 100

            scenarios.append(
                {
                    "action": "Increase Physical Activity",
                    "icon": "running",
                    "current": "Sedentary",
                    "target": "Active lifestyle",
                    "risk_change": round(float(change), 1),
                    "new_risk": round(float(new_prob) * 100, 1),
                    "positive": bool(change > 0),
                }
            )

        # Sort by risk reduction potential
        scenarios.sort(key=lambda x: x["risk_change"], reverse=True)

        return scenarios[:4]  # Return top 4 scenarios

    except Exception as e:
        print(f"What-If Error: {e}")
        return []


@app.route("/")
def home():
    return render_template("landing.html")


@app.route("/assess")
def assess():
    return render_template("assess.html")


@app.route("/results")
def results():
    # Get results from session
    result_data = session.get("result_data", None)
    if not result_data:
        return redirect(url_for("assess"))
    return render_template("results.html", result=result_data)


@app.route("/insights")
def insights():
    return render_template("insights.html", metrics=model_metrics)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/predict", methods=["POST"])
def predict():
    if not model:
        return render_template("assess.html", error="Model failed to load.")

    data = request.form.to_dict()  # Convert to dict for modification in what-if
    errors = validate_input(data)
    if errors:
        return render_template("assess.html", validation_errors=errors, inputs=data)

    try:
        features, bmi = preprocess_input(data)
        prob = float(
            model.predict_proba(features)[0][1]
        )  # Convert to native Python float
        prediction = int(prob >= 0.5)  # Binary prediction

        # Get risk category (3-tier system)
        risk_cat = get_risk_category(prob)
        risk_category = {
            "level": str(risk_cat["label"]),
            "class": str(risk_cat["class"]),
            "color": str(risk_cat["class"]),  # CSS class name
            "description": get_risk_description(risk_cat["label"], prob),
        }

        # Get SHAP explanation
        shap_explanation = get_shap_explanation(features)
        print(f"SHAP explanation returned: {shap_explanation is not None}")

        # Format SHAP factors for template
        shap_factors = []
        human_explanations = []
        if shap_explanation and shap_explanation.get("all_contributions"):

            human_explanations = humanize_shap(
                shap_explanation["all_contributions"][:6]
            )
            print(
                f"Processing {len(shap_explanation['all_contributions'])} contributions"
            )
            for contrib in shap_explanation["all_contributions"][:6]:
                shap_factors.append(
                    {
                        "feature": str(contrib["feature"]),
                        "value": str(round(float(contrib["abs_value"]) * 100, 1)) + "%",
                        "impact": float(contrib["abs_value"]),
                        "direction": (
                            "Increases risk"
                            if contrib["value"] > 0
                            else "Decreases risk"
                        ),
                    }
                )
        print(f"Final shap_factors count: {len(shap_factors)}")

        # Get What-If scenarios
        whatif_raw = calculate_whatif_scenarios(data, prob, features)

        # Format What-If scenarios for template (ensure JSON serializable)
        whatif_scenarios = []
        for scenario in whatif_raw:
            whatif_scenarios.append(
                {
                    "scenario": str(scenario["action"]),
                    "icon": str(scenario["icon"]),
                    "new_probability": float(scenario["new_risk"]) / 100,
                    "change": (
                        float(scenario["risk_change"])
                        if scenario.get("positive", True)
                        else -float(scenario["risk_change"])
                    ),
                }
            )

        # Chart Data
        chart = {
            "user_bmi": round(float(bmi), 1),
            "user_bp": int(data["ap_hi"]),
            "user_pp": int(data["ap_hi"]) - int(data["ap_lo"]),
        }

        # Store in session for results page (all values must be JSON serializable)
        result_data = {
            "prediction": prediction,
            "probability": prob,
            "prediction_text": f"{round(prob*100, 1)}%",
            "prediction_value": round(prob * 100, 1),
            "risk_category": risk_category,
            "chart_data": chart,
            "shap_factors": shap_factors,
            "whatif_scenarios": whatif_scenarios,
            "inputs": data,
            "human_explanations": human_explanations,
            "explanation_note": "Feature explanations are based on the trained prediction model.",
            "clinical_explanation": summarize_explanations(human_explanations),
        }
        session["result_data"] = result_data

        return redirect(url_for("results"))
    except Exception as e:
        import traceback

        traceback.print_exc()
        return render_template("assess.html", error=str(e), inputs=data)


def get_risk_description(level, prob):
    """Generate a description based on risk level."""
    if level == "Low":
        return f"Your cardiovascular risk score of {round(prob*100, 1)}% indicates a low risk. Continue maintaining your healthy lifestyle habits."
    elif level == "Moderate":
        return f"Your cardiovascular risk score of {round(prob*100, 1)}% indicates moderate risk. Consider consulting with a healthcare provider and reviewing lifestyle factors."
    else:
        return f"Your cardiovascular risk score of {round(prob*100, 1)}% indicates elevated risk. We strongly recommend consulting with a healthcare professional for a thorough evaluation."


@app.route("/api/health")
def health_check():
    return jsonify({"status": "ok", "message": "Server is healthy"}), 200


if __name__ == "__main__":
    app.run(debug=True)
