from flask import Flask, jsonify, request

app = Flask(__name__)

import pickle
import numpy as np

# Load pickled model
MODEL_PATH = "model.pkl"

with open(MODEL_PATH, "rb") as f:
    model = pickle.load(f)

    

CLASS_MAP = {0: "setosa", 1: "versicolor", 2: "virginica"}

@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True)
    if not data or "features" not in data:
        return jsonify({"error": "Body must be JSON with a 'features' key"}), 400

    features = data["features"]
    if not isinstance(features, list) or len(features) != 4:
        return jsonify({"error": "'features' must be a list of 4 numbers"}), 400

    try:
        sample = np.array([features], dtype=float)
        class_idx = int(model.predict(sample)[0])
    except Exception as e:
        app.logger.exception("Prediction failed")
        return jsonify({"error": "Prediction failed", "detail": str(e)}), 500

    return jsonify({
        "prediction": class_idx,
        "class_name": CLASS_MAP.get(class_idx, "unknown"),
    }), 200

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(debug=True)