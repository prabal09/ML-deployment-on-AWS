"""
teardown_serverless.py — Delete the serverless endpoint, config, and model.

Same logic as teardown_realtime.py but targets the serverless endpoint.
Serverless endpoints bill $0 when idle, so this is less time-critical than
tearing down a real-time endpoint — but still good hygiene.
"""

import boto3
from botocore.exceptions import ClientError


REGION = "us-east-2"
ENDPOINT_NAME = "iris-serverless-endpoint"


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

    print("\nServerless teardown complete.")


if __name__ == "__main__":
    main()