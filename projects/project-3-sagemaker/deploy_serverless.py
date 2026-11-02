"""
deploy_serverless.py — Deploy the Iris classifier as a SageMaker serverless endpoint.

Same Model + container + model.tar.gz + inference.py as the real-time endpoint,
but with ServerlessInferenceConfig instead of (instance_type, instance_count).

Serverless endpoints bill per invocation + GB-second of compute; idle = $0.
First invocation after idle has a cold-start of 1-5 seconds while SageMaker
loads the container.
"""

import boto3
import sagemaker
from sagemaker.sklearn.model import SKLearnModel
from sagemaker.serverless import ServerlessInferenceConfig


REGION = "us-east-2"
BUCKET = "prabal-sagemaker-s3-artifacts-us-east-2"
MODEL_S3_URI = f"s3://{BUCKET}/iris/model.tar.gz"
ROLE_NAME = "SageMakerExecutionRole-iris"
ENDPOINT_NAME = "iris-serverless-endpoint"
FRAMEWORK_VERSION = "1.2-1"


def main():
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    print(f"Using role: {role_arn}")

    session = sagemaker.Session()

    model = SKLearnModel(
        model_data=MODEL_S3_URI,
        role=role_arn,
        entry_point="inference.py",
        framework_version=FRAMEWORK_VERSION,
        sagemaker_session=session,
    )

    # Serverless config: memory + max concurrent executions.
    # Memory options: 1024, 2048, 3072, 4096, 5120, 6144 MB.
    # 1024 MB is cheapest and more than enough for Iris.
    serverless_config = ServerlessInferenceConfig(
        memory_size_in_mb=1024,
        max_concurrency=2,
    )

    print(f"Deploying serverless endpoint '{ENDPOINT_NAME}' ... (3-6 min)")
    predictor = model.deploy(
        serverless_inference_config=serverless_config,
        endpoint_name=ENDPOINT_NAME,
    )

    print(f"\nEndpoint '{predictor.endpoint_name}' is InService.")
    print(f"  Billing: $0 when idle; ~$0.20/M requests + ~$0.00017/GB-sec active")
    print(f"\nFirst invoke will have a cold start of 1-5 sec.")
    print(f"Test with:  python invoke_serverless.py")
    print(f"Teardown:   python teardown_serverless.py")


if __name__ == "__main__":
    main()