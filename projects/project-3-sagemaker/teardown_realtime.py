"""
teardown_realtime.py — Delete the Iris real-time endpoint and its artifacts.

Deletes in the correct order:
  Endpoint         (stops billing immediately)
  EndpointConfig   (no standing cost; cleanup only)
  Model            (no standing cost; cleanup only)

Run this immediately after Phase E testing to stop billing.
"""

import boto3
from botocore.exceptions import ClientError


REGION = "us-east-2"
ENDPOINT_NAME = "iris-rt-endpoint"
# EndpointConfig and Model are named by the SDK with the endpoint name as prefix
# when model.deploy() is used. We discover them via describe_endpoint.


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

    # Discover the Model name(s) from the EndpointConfig's production variants.
    config = client.describe_endpoint_config(EndpointConfigName=endpoint_config_name)
    model_names = [v["ModelName"] for v in config["ProductionVariants"]]

    print(f"Deleting endpoint '{ENDPOINT_NAME}' ...")
    client.delete_endpoint(EndpointName=ENDPOINT_NAME)

    print(f"Deleting endpoint config '{endpoint_config_name}' ...")
    client.delete_endpoint_config(EndpointConfigName=endpoint_config_name)

    for model_name in model_names:
        print(f"Deleting model '{model_name}' ...")
        client.delete_model(ModelName=model_name)

    print("\nTeardown complete. Billing has stopped.")


if __name__ == "__main__":
    main()