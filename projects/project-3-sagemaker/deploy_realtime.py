"""
deploy_realtime.py — Deploy the Iris classifier as a SageMaker real-time endpoint.

Creates a Model (points at model.tar.gz in S3), EndpointConfig (instance type +
count), and Endpoint (actual running infrastructure) in one SDK call. Takes
~5-10 minutes for the endpoint to reach InService.

Prerequisites:
  - model.tar.gz uploaded to s3://.../iris/model.tar.gz
  - SageMakerExecutionRole-iris exists with AmazonSageMakerFullAccess
  - aws configure done locally; `aws sts get-caller-identity` works
"""

import boto3
import sagemaker
from sagemaker.sklearn.model import SKLearnModel


REGION = "us-east-2"
BUCKET = "prabal-sagemaker-s3-artifacts-us-east-2"
MODEL_S3_URI = f"s3://{BUCKET}/iris/model.tar.gz"
ROLE_NAME = "SageMakerExecutionRole-iris"
ENDPOINT_NAME = "iris-rt-endpoint"

# SageMaker's prebuilt sklearn container version. 1.2-1 is widely supported
# across SDK versions and should load our model.pkl despite the training-time
# sklearn being a bit newer (sklearn's pickle format is backward-compatible
# for basic estimators like RandomForest).
FRAMEWORK_VERSION = "1.2-1"


def main():
    # Build the role ARN from current STS identity so the script is portable
    # across AWS accounts.
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    print(f"Using role: {role_arn}")

    session = sagemaker.Session()

    # entry_point tells the SDK which module the container should import
    # (sets SAGEMAKER_PROGRAM env var).
    #
    # NO source_dir — if we specified one, the SDK would upload the entire
    # directory (including requirements.txt), and the container would try to
    # pip install everything in it. Our requirements.txt is tuned for the
    # local Python 3.12 client; the container runs Python 3.9 and only needs
    # inference.py's imports (numpy, pickle, json, os) which it already has.
    # Omitting source_dir makes the SDK upload only inference.py.
    model = SKLearnModel(
        model_data=MODEL_S3_URI,
        role=role_arn,
        entry_point="inference.py",
        framework_version=FRAMEWORK_VERSION,
        sagemaker_session=session,
    )

    print(f"Deploying endpoint '{ENDPOINT_NAME}' ... (5-10 min)")
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type="ml.t2.medium",
        endpoint_name=ENDPOINT_NAME,
    )

    print(f"\nEndpoint '{predictor.endpoint_name}' is InService.")
    print(f"  Instance type: ml.t2.medium (billing: ~$0.056/hour)")
    print(f"  Model artifact: {MODEL_S3_URI}")
    print(f"\nTEST THEN TEAR DOWN. Billing continues until the endpoint is deleted.")
    print(f"  Teardown:  python teardown_realtime.py")


if __name__ == "__main__":
    main()