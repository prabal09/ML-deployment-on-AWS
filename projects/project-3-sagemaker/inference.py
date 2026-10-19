"""
inference.py — SageMaker inference handlers for the Iris classifier.

SageMaker's prebuilt sklearn container imports this module and calls the
four handler functions below. We never run an HTTP server ourselves; the
container does that and dispatches requests to these handlers.
"""

import json
import os
import pickle

import numpy as np


CLASS_MAP = {0: "setosa", 1: "versicolor", 2: "virginica"}


def model_fn(model_dir):
    """
    Load the trained model from disk. Called once at container startup.

    SageMaker extracts the contents of model.tar.gz into `model_dir`, so our
    pickled model lives at `<model_dir>/model.pkl`. The returned object is
    held in memory for the container's lifetime and passed to predict_fn on
    every subsequent request.
    """
    model_path = os.path.join(model_dir, "model.pkl")
    with open(model_path, "rb") as f:
        return pickle.load(f)


def input_fn(request_body, content_type):
    """
    Parse the raw HTTP request body into a 2D numpy array that scikit-learn
    accepts. Called once per inbound request.

    Supports a single sample ({"features": [5.1, 3.5, 1.4, 0.2]}) or a batch
    ({"instances": [[5.1, 3.5, 1.4, 0.2], [6.2, 3.4, 5.4, 2.3]]}). Returns
    shape (n_samples, 4) in both cases.
    """
    if content_type != "application/json":
        raise ValueError(f"Unsupported content type: {content_type}")

    data = json.loads(request_body)

    if "features" in data:
        return np.array([data["features"]], dtype=float)
    if "instances" in data:
        return np.array(data["instances"], dtype=float)

    raise ValueError("Body must contain either 'features' (single) or 'instances' (batch)")


def predict_fn(input_data, model):
    """
    Run the model on the parsed input. Called once per request.

    Returns a list of result dicts (one per input row) with the class index
    and human-readable name. Letting predict_fn produce structured results
    keeps output_fn trivial.
    """
    class_indices = model.predict(input_data)
    return [
        {"prediction": int(idx), "class_name": CLASS_MAP.get(int(idx), "unknown")}
        for idx in class_indices
    ]


def output_fn(prediction, accept):
    """
    Serialize the prediction into the HTTP response body. Called once per
    request after predict_fn.

    For a single-sample input, unwrap the one-element list into a bare dict
    so the response matches the shape of the input. For batches, keep the
    list.
    """
    if accept != "application/json":
        raise ValueError(f"Unsupported accept type: {accept}")

    payload = prediction[0] if len(prediction) == 1 else prediction
    return json.dumps(payload), "application/json"