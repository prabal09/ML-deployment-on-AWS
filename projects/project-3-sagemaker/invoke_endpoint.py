"""
invoke_endpoint.py — Three ways to invoke the SageMaker real-time endpoint.

Each method hits the same endpoint and gets the same prediction. They differ
in abstraction level:
  Method 1 — SageMaker SDK:  highest-level, 2 lines, reusable Predictor
  Method 2 — boto3:          mid-level, direct AWS API client
  Method 3 — AWS CLI:        lowest-level, pure shell / HTTP

Run all three to see them produce identical predictions.
"""

import json

import boto3
import sagemaker
from sagemaker.sklearn.model import SKLearnPredictor
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer


REGION = "us-east-2"
ENDPOINT_NAME = "iris-rt-endpoint"

# One sample Iris features: sepal_length, sepal_width, petal_length, petal_width
SINGLE_SAMPLE = {"features": [5.1, 3.5, 1.4, 0.2]}

# A batch of three samples
BATCH_SAMPLES = {
    "instances": [
        [5.1, 3.5, 1.4, 0.2],  # expected: setosa (0)
        [6.2, 3.4, 5.4, 2.3],  # expected: virginica (2)
        [5.9, 3.0, 5.1, 1.8],  # expected: virginica (2)
    ]
}


def method_1_sagemaker_sdk():
    """
    Highest-level: construct a Predictor from the endpoint name, call .predict().

    The SDK handles serialization (dict → JSON), signing, HTTP, and
    deserialization (JSON → dict) via the serializer/deserializer instances.
    """
    print("=" * 60)
    print("Method 1 — SageMaker SDK (Predictor)")
    print("=" * 60)

    predictor = SKLearnPredictor(
        endpoint_name=ENDPOINT_NAME,
        sagemaker_session=sagemaker.Session(),
        serializer=JSONSerializer(),
        deserializer=JSONDeserializer(),
    )

    result = predictor.predict(SINGLE_SAMPLE)
    print(f"Single sample result: {result}")

    result = predictor.predict(BATCH_SAMPLES)
    print(f"Batch result:         {result}")
    print()


def method_2_boto3():
    """
    Mid-level: direct boto3 call to sagemaker-runtime.

    You manually serialize the body to bytes and set Content-Type / Accept
    headers. Same API that the SageMaker SDK calls internally.
    """
    print("=" * 60)
    print("Method 2 — boto3 (sagemaker-runtime client)")
    print("=" * 60)

    client = boto3.client("sagemaker-runtime", region_name=REGION)

    response = client.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Accept="application/json",
        Body=json.dumps(SINGLE_SAMPLE).encode("utf-8"),
    )
    body = response["Body"].read().decode("utf-8")
    print(f"Single sample result: {body}")

    response = client.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Accept="application/json",
        Body=json.dumps(BATCH_SAMPLES).encode("utf-8"),
    )
    body = response["Body"].read().decode("utf-8")
    print(f"Batch result:         {body}")
    print()


def method_3_aws_cli_example():
    """
    Lowest-level: print the AWS CLI command to run.

    The CLI uses the same sagemaker-runtime API as boto3. Shown here as a
    printed command rather than executed so you see the shell shape clearly.
    """
    print("=" * 60)
    print("Method 3 — AWS CLI (run from shell separately)")
    print("=" * 60)

    cmd = (
        f'aws sagemaker-runtime invoke-endpoint '
        f'--endpoint-name {ENDPOINT_NAME} '
        f'--region {REGION} '
        f'--content-type application/json '
        f'--accept application/json '
        f'--body \'{json.dumps(SINGLE_SAMPLE)}\' '
        f'--cli-binary-format raw-in-base64-out '
        f'response.json && cat response.json'
    )
    print("Run from shell:")
    print(f"  {cmd}")
    print()


if __name__ == "__main__":
    method_1_sagemaker_sdk()
    method_2_boto3()
    method_3_aws_cli_example()
