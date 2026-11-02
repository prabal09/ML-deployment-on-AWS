"""
batch_transform.py — Run a SageMaker Batch Transform job on the Iris model.

Processes batch_input.jsonl in S3 → writes predictions to S3. No persistent
endpoint; instance(s) spin up for the job's duration, then terminate.

Workflow:
  1. Upload batch_input.jsonl to S3 (via aws s3 cp — see Suggested move)
  2. Run this script
  3. Script waits for job completion (~5-10 min)
  4. Download the output from S3 and verify

Billing: only for job duration (instance-hours while the job runs).
"""

import boto3
import sagemaker
from sagemaker.sklearn.model import SKLearnModel


REGION = "us-east-2"
BUCKET = "prabal-sagemaker-s3-artifacts-us-east-2"
MODEL_S3_URI = f"s3://{BUCKET}/iris/model.tar.gz"
INPUT_S3 = f"s3://{BUCKET}/iris-batch/input/batch_input.jsonl"
OUTPUT_S3 = f"s3://{BUCKET}/iris-batch/output/"
ROLE_NAME = "SageMakerExecutionRole-iris"
FRAMEWORK_VERSION = "1.2-1"


def main():
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    print(f"Using role: {role_arn}")

    session = sagemaker.Session()

    # Same Model definition as the real-time and serverless deploys — reuses
    # model.tar.gz in S3 and inference.py from local directory.
    model = SKLearnModel(
        model_data=MODEL_S3_URI,
        role=role_arn,
        entry_point="inference.py",
        framework_version=FRAMEWORK_VERSION,
        sagemaker_session=session,
    )

    # Transformer config:
    #   strategy="SingleRecord"   → one input line = one container invocation
    #   assemble_with="Line"      → outputs assembled into one file, newline-separated
    #   accept="application/json" → container returns JSON per invocation
    transformer = model.transformer(
        instance_count=1,
        instance_type="ml.m5.large",
        output_path=OUTPUT_S3,
        strategy="SingleRecord",
        assemble_with="Line",
        accept="application/json",
    )

    print(f"\nStarting Batch Transform job ...")
    print(f"  Input:  {INPUT_S3}")
    print(f"  Output: {OUTPUT_S3}")
    print(f"  Instance: ml.m5.large (billing ~$0.115/hour, only while job runs)")
    print(f"  Expected duration: 5-10 min (dominated by provisioning overhead)\n")

    transformer.transform(
        data=INPUT_S3,
        content_type="application/json",
        split_type="Line",     # split input file by newlines
        wait=True,             # block until job completes
        logs=True,             # stream CloudWatch logs to this terminal
    )

    print(f"\nJob complete.")
    print(f"Output file (one line per input prediction):")
    print(f"  {OUTPUT_S3}batch_input.jsonl.out")
    print(f"\nDownload with:")
    print(f"  aws s3 cp {OUTPUT_S3}batch_input.jsonl.out .")


if __name__ == "__main__":
    main()