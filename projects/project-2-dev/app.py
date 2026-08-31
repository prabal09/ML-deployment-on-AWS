from flask import Flask, jsonify

app = Flask(__name__)

import pickle
import numpy as np

# Load pickled model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)


@app.route('/predict/<float:sepal_length>/<float:sepal_width>/<float:petal_length>/<float:petal_width>', methods=['GET'])
def predict(sepal_length, sepal_width, petal_length, petal_width):
    # Predict on new sample: [sepal length, sepal width, petal length, petal width]
    # sample input : np.array([[5.1, 3.5, 1.4, 0.2]])
    # returns the predicted class index (0, 1, or 2)

    sample = np.array([[sepal_length, sepal_width, petal_length, petal_width]])

    prediction = model.predict(sample)

    print(f"Predicted class index: {prediction[0]}")
    class_idx = int(prediction[0])  # Convert NumPy int to Python int

    return jsonify({"prediction": class_idx})

if __name__ == '__main__':
    app.run(debug=True)