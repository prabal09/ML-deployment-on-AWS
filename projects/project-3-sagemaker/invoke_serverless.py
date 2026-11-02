"""
invoke_serverless.py — Invoke the serverless endpoint and time the cold start.

Same three methods as invoke_endpoint.py (SDK, boto3, CLI example), but
times each invocation so you can see the cold-start cost on the first call
and the warm latency on subsequent calls.
"""

import json
import time

import boto3
import sagemaker
from sagemaker.sklearn.model import SKLearnPredictor
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer


REGION = "us-east-2"
ENDPOINT_NAME = "iris-serverless-endpoint"

SINGLE_SAMPLE = {"features": [5.1, 3.5, 1.4, 0.2]}
BATCH_SAMPLES = {
    "instances": [
        [5.1, 3.5, 1.4, 0.2],
        [6.2, 3.4, 5.4, 2.3],
        [5.9, 3.0, 5.1, 1.8],
    ]
}


def _timed_invoke(client, body):
    t0 = time.monotonic()
    response = client.invoke_endpoint(
        EndpointName=ENDPOINT_NAME,
        ContentType="application/json",
        Accept="application/json",
        Body=json.dumps(body).encode("utf-8"),
    )
    elapsed_ms = (time.monotonic() - t0) * 1000
    result = response["Body"].read().decode("utf-8")
    return result, elapsed_ms


def main():
    client = boto3.client("sagemaker-runtime", region_name=REGION)

    print("=" * 60)
    print("Serverless invocation sequence")
    print("=" * 60)

    # First invocation = cold start
    result, ms = _timed_invoke(client, SINGLE_SAMPLE)
    print(f"Call 1 (COLD): {ms:.0f}ms  → {result}")

    # Subsequent invocations = warm
    for i in range(2, 6):
        result, ms = _timed_invoke(client, SINGLE_SAMPLE)
        print(f"Call {i} (warm): {ms:.0f}ms  → {result}")

    # Batch invocation
    result, ms = _timed_invoke(client, BATCH_SAMPLES)
    print(f"\nBatch call: {ms:.0f}ms")
    print(f"  → {result}")

    print(f"\nNote: Serverless endpoints go cold after ~15 min idle.")
    print(f"Teardown when done:  python teardown_serverless.py")


if __name__ == "__main__":
    main()