"""
teardown_async.py — Delete the async endpoint, config, and model.

Same logic as teardown_realtime.py / teardown_serverless.py but targets the
async endpoint. Async runs on dedicated instances (billing like real-time), so
this IS time-critical — an idle async endpoint keeps charging for its instance
until deleted.

Note: this deletes the endpoint/config/model only. The S3 objects under the
iris-async/input, /output, and /failure prefixes are left in place — delete
them separately with `aws s3 rm` if you want a clean bucket.
"""

import boto3
from botocore.exceptions import ClientError


REGION = "us-east-2"
ENDPOINT_NAME = "iris-async-endpoint"


def main():
    client = boto3.client("sagemaker", region_name=REGION)

    try:
        desc = client.describe_endpoint(EndpointName=ENDPOINT_NAME)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ValidationException":
            print(f"Endpoint '{ENDPOINT_NAME}' does not exist. Nothing to tear down.")
            return
        raise

    endpoint_config_name = desc["EndpointConfigName"]
    config = client.describe_endpoint_config(EndpointConfigName=endpoint_config_name)
    model_names = [v["ModelName"] for v in config["ProductionVariants"]]

    print(f"Deleting endpoint '{ENDPOINT_NAME}' ...")
    client.delete_endpoint(EndpointName=ENDPOINT_NAME)

    print(f"Deleting endpoint config '{endpoint_config_name}' ...")
    client.delete_endpoint_config(EndpointConfigName=endpoint_config_name)

    for model_name in model_names:
        print(f"Deleting model '{model_name}' ...")
        client.delete_model(ModelName=model_name)

    print("\nAsync teardown complete.")
    print("S3 input/output/failure objects left intact — remove with `aws s3 rm` if desired.")


if __name__ == "__main__":
    main()
