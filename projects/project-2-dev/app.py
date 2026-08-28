import pickle
import numpy as np

# Load pickled model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)


@app.route('/predict')
def predict(sample):
    # Predict on new sample: [sepal length, sepal width, petal length, petal width]
    # sample = np.array([[5.1, 3.5, 1.4, 0.2]])
    prediction = model.predict(sample)
    print(f"Predicted class index: {prediction[0]}")
    return prediction[0]