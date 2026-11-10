"""
invoke_async.py — Invoke the async endpoint and wait for the S3 result.

The async invocation model is fundamentally different from invoke_endpoint.py
and invoke_serverless.py, which both get a prediction back inline:

  1. Upload the request payload to S3 (async takes an S3 InputLocation,
     NOT an HTTP body).
  2. Call invoke_endpoint_async — this returns IMMEDIATELY with an
     OutputLocation (an S3 URI) and an InferenceId. No prediction yet.
  3. Poll S3 until the output object appears, then read it. (In production
     you'd subscribe to the SNS SuccessTopic instead of polling.)

This "submit, then come back for it" flow is the whole point of async — the
caller is never blocked on an open connection while the model runs.
"""

import json
import time

import boto3
from botocore.exceptions import ClientError


REGION = "us-east-2"
BUCKET = "prabal-sagemaker-s3-artifacts-us-east-2"
ENDPOINT_NAME = "iris-async-endpoint"
INPUT_PREFIX = "iris-async/input"

SINGLE_SAMPLE = {"features": [5.1, 3.5, 1.4, 0.2]}
BATCH_SAMPLES = {
    "instances": [
        [5.1, 3.5, 1.4, 0.2],  # expected: setosa (0)
        [6.2, 3.4, 5.4, 2.3],  # expected: virginica (2)
        [5.9, 3.0, 5.1, 1.8],  # expected: virginica (2)
    ]
}

POLL_INTERVAL_SEC = 2
POLL_TIMEOUT_SEC = 120


def _split_s3_uri(uri):
    """s3://bucket/key/parts -> ('bucket', 'key/parts')."""
    without_scheme = uri.replace("s3://", "", 1)
    bucket, _, key = without_scheme.partition("/")
    return bucket, key


def _upload_input(s3_client, body, key_name):
    """Put the request payload in S3 and return its s3:// URI."""
    key = f"{INPUT_PREFIX}/{key_name}"
    s3_client.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(body).encode("utf-8"),
        ContentType="application/json",
    )
    return f"s3://{BUCKET}/{key}"


def _wait_for_output(s3_client, output_uri):
    """Poll S3 until the output object exists, then return its decoded body."""
    out_bucket, out_key = _split_s3_uri(output_uri)
    deadline = time.monotonic() + POLL_TIMEOUT_SEC

    while time.monotonic() < deadline:
        try:
            obj = s3_client.get_object(Bucket=out_bucket, Key=out_key)
            return obj["Body"].read().decode("utf-8")
        except ClientError as e:
            # NoSuchKey / 404 just means "not written yet" — keep polling.
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                time.sleep(POLL_INTERVAL_SEC)
                continue
            raise

    raise TimeoutError(
        f"Output {output_uri} did not appear within {POLL_TIMEOUT_SEC}s. "
        f"Check the failure prefix and CloudWatch logs for the endpoint."
    )


def _invoke_and_wait(runtime_client, s3_client, body, key_name, label):
    input_uri = _upload_input(s3_client, body, key_name)

    t0 = time.monotonic()
    response = runtime_client.invoke_endpoint_async(
        EndpointName=ENDPOINT_NAME,
        InputLocation=input_uri,
        ContentType="application/json",
        Accept="application/json",
    )
    output_uri = response["OutputLocation"]
    inference_id = response.get("InferenceId", "n/a")
    submit_ms = (time.monotonic() - t0) * 1000

    print(f"\n[{label}]")
    print(f"  submitted in {submit_ms:.0f}ms (returns before inference runs)")
    print(f"  InferenceId:    {inference_id}")
    print(f"  InputLocation:  {input_uri}")
    print(f"  OutputLocation: {output_uri}")

    result = _wait_for_output(s3_client, output_uri)
    total_ms = (time.monotonic() - t0) * 1000
    print(f"  result (after {total_ms:.0f}ms end-to-end): {result}")


def main():
    runtime_client = boto3.client("sagemaker-runtime", region_name=REGION)
    s3_client = boto3.client("s3", region_name=REGION)

    print("=" * 60)
    print("Async invocation sequence (submit -> poll S3 for result)")
    print("=" * 60)

    _invoke_and_wait(
        runtime_client, s3_client, SINGLE_SAMPLE, "single.json", "single sample"
    )
    _invoke_and_wait(
        runtime_client, s3_client, BATCH_SAMPLES, "batch.json", "batch samples"
    )

    print(f"\nNote: unlike the sync endpoints, the result is an S3 object, not an")
    print(f"HTTP response body. In production you'd react to the SNS SuccessTopic")
    print(f"instead of polling.")
    print(f"Teardown when done:  python teardown_async.py")


if __name__ == "__main__":
    main()
