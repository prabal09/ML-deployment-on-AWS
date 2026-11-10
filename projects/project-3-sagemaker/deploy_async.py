"""
deploy_async.py — Deploy the Iris classifier as a SageMaker asynchronous endpoint.

Same Model + container + model.tar.gz + inference.py as the real-time and
serverless deploys, but with AsyncInferenceConfig. An async endpoint is the
fourth deployment mode: a persistent endpoint (like real-time) fronted by an
internal request queue, where requests come in as S3 objects and results are
written back to S3 — the caller never blocks waiting for the prediction.

How it differs from the others:
  - real-time   : dedicated instances, synchronous, payload in/out over HTTP
  - serverless  : scales 0->N, synchronous, payload in/out over HTTP
  - async       : dedicated instances + queue, INPUT from S3, OUTPUT to S3,
                  caller gets an output location immediately and polls for it
  - batch       : no persistent endpoint; a one-off job over a whole S3 file

Why you'd pick async: large payloads (up to 1 GB) and/or long inference
(up to ~60 min) where a caller still wants *their* result back but can't hold
an HTTP connection open. For Iris this is overkill functionally — the point is
to demonstrate and be able to explain the queue-backed, S3-I/O pattern.

Prerequisites:
  - model.tar.gz uploaded to s3://.../iris/model.tar.gz
  - SageMakerExecutionRole-iris exists with AmazonSageMakerFullAccess
    (needs S3 read on the input prefix + S3 write on the output prefix)
  - aws configure done locally; `aws sts get-caller-identity` works
"""

import boto3
import sagemaker
from sagemaker.sklearn.model import SKLearnModel
from sagemaker.async_inference import AsyncInferenceConfig


REGION = "us-east-2"
BUCKET = "prabal-sagemaker-s3-artifacts-us-east-2"
MODEL_S3_URI = f"s3://{BUCKET}/iris/model.tar.gz"
ROLE_NAME = "SageMakerExecutionRole-iris"
ENDPOINT_NAME = "iris-async-endpoint"
FRAMEWORK_VERSION = "1.2-1"

# Where SageMaker writes results (one object per invocation) and, separately,
# where it records failures. Both are plain S3 prefixes in the same bucket.
OUTPUT_S3 = f"s3://{BUCKET}/iris-async/output/"
FAILURE_S3 = f"s3://{BUCKET}/iris-async/failure/"


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

    # The one thing that makes this endpoint async: an AsyncInferenceConfig.
    #   output_path  — REQUIRED. Results land here as <uuid>.out objects.
    #   failure_path — optional. Error records land here instead of output_path.
    #   max_concurrent_invocations_per_instance — how many queued requests one
    #       instance processes at once before the queue backs up.
    #   notification_config (commented) — SNS topics pinged on success/error so
    #       a caller can be event-driven instead of polling S3.
    async_config = AsyncInferenceConfig(
        output_path=OUTPUT_S3,
        failure_path=FAILURE_S3,
        max_concurrent_invocations_per_instance=4,
        # notification_config={
        #     "SuccessTopic": f"arn:aws:sns:{REGION}:{account_id}:iris-async-success",
        #     "ErrorTopic":   f"arn:aws:sns:{REGION}:{account_id}:iris-async-error",
        # },
    )

    # Unlike serverless, async runs on real instances (instance_type + count),
    # just like real-time — the difference is the queue + S3 I/O, not the compute.
    print(f"Deploying async endpoint '{ENDPOINT_NAME}' ... (5-10 min)")
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type="ml.t2.medium",
        async_inference_config=async_config,
        endpoint_name=ENDPOINT_NAME,
    )

    print(f"\nEndpoint '{predictor.endpoint_name}' is InService.")
    print(f"  Instance type: ml.t2.medium (billing: ~$0.056/hour while >=1 instance)")
    print(f"  Input:   upload request objects under s3://{BUCKET}/iris-async/input/")
    print(f"  Output:  {OUTPUT_S3}")
    print(f"  Failure: {FAILURE_S3}")
    print(f"\nUnlike serverless, async bills like real-time: an always-on instance.")
    print(f"To get serverless-like idle economics, attach an application-autoscaling")
    print(f"policy on ApproximateBacklogSizePerInstance to scale this endpoint to 0.")
    print(f"\nTEST THEN TEAR DOWN. Billing continues until the endpoint is deleted.")
    print(f"  Test:     python invoke_async.py")
    print(f"  Teardown: python teardown_async.py")


if __name__ == "__main__":
    main()
