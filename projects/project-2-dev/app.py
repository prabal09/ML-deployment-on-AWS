from flask import Flask, jsonify, request

app = Flask(__name__)

import pickle
import numpy as np

# Load pickled model
try:
    with open("model.pkl", "rb") as f:
        model = pickle.load(f)
except FileNotFoundError:
    print("Error: model.pkl file not found. Please ensure the model file is present in the correct directory.")
    raise FileNotFoundError(
        f"'{MODEL_PATH}' not found. Run train.py first to generate the model artifact."
    )
    

CLASS_MAP = {0: "setosa", 1: "versicolor", 2: "virginica"}

@app.route('/predict', methods=['GET'])
def predict():
    # Predict on new sample: [sepal length, sepal width, petal length, petal width]
    # sample input : np.array([[5.1, 3.5, 1.4, 0.2]])
    # returns the predicted class index (0, 1, or 2)
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing or invalid JSON body"})
    sample = np.array([data["features"]])

    prediction = model.predict(sample)

    
    class_idx = int(prediction[0])  # Convert NumPy int to Python int
    class_name: CLASS_MAP.get(pred_idx, "unknown")
    print(f"Predicted class index: {class_idx}, class name: {class_name}")

    return jsonify({"prediction": class_idx,
                    "class_name": class_name})

if __name__ == '__main__':
    app.run(debug=True)