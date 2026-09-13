"""
train.py
--------
Trains a Random Forest classifier on the Iris dataset, reports test metrics,
and serializes the trained model using pickle to 'model.pkl'.
"""

import pickle
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split


def main() -> None:
    # 1. Load dataset
    print("Loading Iris dataset...")
    iris = load_iris()
    X, y = iris.data, iris.target

    # 2. Train / Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # 3. Initialize & Train Model
    print("Training Random Forest Classifier...")
    clf = RandomForestClassifier(
        n_estimators=100, max_depth=3, random_state=42, n_jobs=-1
    )
    clf.fit(X_train, y_train)

    # 4. Evaluate
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print("\n--- Model Evaluation ---")
    print(f"Test Accuracy: {acc:.4f}\n")
    print("Classification Report:")
    print(
        classification_report(
            y_test, y_pred, target_names=iris.target_names
        )
    )

    # 5. Export Model Artifact with Pickle
    model_filename = "model.pkl"
    with open(model_filename, "wb") as f:
        pickle.dump(clf, f)
    print(f"Model saved successfully to '{model_filename}'.")


if __name__ == "__main__":
    main()