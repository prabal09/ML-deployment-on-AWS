# Project 3 — SageMaker Managed Inference

Deploying the same scikit-learn Iris classifier via Amazon SageMaker's three
inference modes — real-time endpoint, serverless inference, and batch
transform. First encounter with AWS's managed ML platform; a deliberate
contrast to the hand-built stacks of Projects 2 and 2.5.

**Status:** not started — begins after Project 2.5 teardown complete

## Goal

Take the same `train.py` + `model.pkl` from Project 2.5 and deploy it three
ways via SageMaker, feeling the differences in cost, latency, and operational
model. Produce one live, invokable endpoint per mode (modes can be stood up,
tested, and torn down independently). The point of this project is to
internalize what SageMaker *takes away* (the whole hand-built serving stack
from Project 2.5) and what it *introduces* (packaging conventions, execution
roles, three distinct billing models).

## Architecture — three deployment modes

### Real-time endpoint

```
Client (boto3 / SageMaker SDK / HTTPS SigV4)
       │
       │ POST ...sagemaker.us-east-2.amazonaws.com/endpoints/iris-rt/invocations
       ▼
   SageMaker Managed Endpoint  (always-on, hourly billing per instance)
       │
       │ container runtime (prebuilt sklearn image or BYOC)
       │ loads model.tar.gz from S3 on start
       ▼
   inference.py → model.predict() → response
```

### Serverless inference

```
Client (boto3 / SageMaker SDK)
       │
       ▼
   SageMaker Serverless Endpoint  (auto-scales 0 → N; cold start on first invoke)
       │
       │ same container, same model.tar.gz
       │ idle = $0, warm invokes = ~10-50ms
       ▼
   inference.py → model.predict() → response
```

### Batch Transform

```
Input CSV in S3  (s3://my-bucket/batch-input/features.csv)
       │
       ▼
   SageMaker Batch Transform Job  (spin up N instances, process, terminate)
       │
       │ same container, same model.tar.gz
       │ runs offline; writes predictions directly to S3
       ▼
Output JSON in S3  (s3://my-bucket/batch-output/predictions.json)
```

## Key changes vs Project 2.5

- **No instances to manage.** No Launch Template, no ASG, no ALB, no Target
  Group, no Security Groups you author. SageMaker runs the serving stack.
- **No nginx, no gunicorn, no systemd.** AWS provides a container image that
  loads your model and serves predictions over HTTPS.
- **Model artifact lives in S3, not git.** `model.tar.gz` is uploaded once;
  endpoint reads it at start. First real use of S3 in this learning path.
- **IAM execution role replaces security groups** as the primary access
  control. SageMaker needs explicit permission to read S3, write CloudWatch
  logs, pull container images from ECR.
- **TLS is handled entirely by AWS** — invocation URL is SigV4-authenticated
  HTTPS. No ACM, no Route 53, no cert management of any kind in this project.
- **Pricing shifts from "hours running" to "mode-specific":** real-time
  endpoints bill like EC2 but with a managed-service premium; serverless is
  per-invocation; batch is per-job-duration.

## The one thing that makes this project work

SageMaker's **packaging convention**:

- `model.tar.gz` contains `model.pkl` + any dependent files.
- An `inference.py` script defines four handler functions SageMaker calls:
  `model_fn(model_dir)` — load the model from disk
  `input_fn(request_body, content_type)` — parse the request
  `predict_fn(input_data, model)` — run inference
  `output_fn(prediction, accept_type)` — serialize the response
- The tarball is uploaded to S3; SageMaker's prebuilt sklearn container
  (`763104351884.dkr.ecr.us-east-2.amazonaws.com/sagemaker-scikit-learn:...`)
  mounts the tarball, imports `inference.py`, and routes HTTPS requests to
  the handler chain.

Everything downstream (endpoints, serverless, batch) consumes this same
`model.tar.gz` + `inference.py` artifact. Build it once, deploy three ways.

## Prerequisites

- Project 2 or 2.5's `train.py` (reused unchanged) producing `model.pkl`
- AWS credentials configured locally (`aws configure`) — Project 3 uses the
  AWS CLI / boto3 extensively, not just the console
- Python environment with `sagemaker` and `boto3` SDKs installed:

  ```bash
  pip install sagemaker boto3
  ```

- An S3 bucket to hold `model.tar.gz` and batch I/O. Will create one as part
  of Phase B: `prabal-sagemaker-artifacts` or similar.
- SageMaker-eligible region (`us-east-2` fine — consistent with Project 2.5).
- A `$25/month` AWS Budgets alert specifically on SageMaker, set before
  Phase D. Real-time endpoints bill continuously and are easy to forget.

## Deployment plan

| Phase | What | Where |
|-------|------|-------|
| A | Author `inference.py` with the four SageMaker handler functions; package `model.pkl` + `inference.py` into `model.tar.gz` locally | Local |
| B | Create S3 bucket; upload `model.tar.gz` | AWS Console / CLI |
| C | Create SageMaker execution role with S3 read + CloudWatch write permissions | IAM |
| D | Deploy a real-time endpoint: Model → EndpointConfig → Endpoint | SageMaker SDK |
| E | Invoke the real-time endpoint via SageMaker SDK, boto3, and AWS CLI | Local |
| F | Deploy a serverless-inference variant from the same model artifact | SageMaker SDK |
| G | Run a batch transform job against a CSV in S3 | SageMaker SDK |
| H | Teardown each mode; review billed cost by mode | AWS Console |

## What I'm learning here

- SageMaker's Model / EndpointConfig / Endpoint three-resource mental model
- Prebuilt framework containers vs BYOC (bring-your-own-container)
- The `inference.py` handler-function convention (model_fn / input_fn /
  predict_fn / output_fn)
- SageMaker Python SDK (`sagemaker.sklearn.model.SKLearnModel`,
  `.deploy()`, `.predict()`) vs raw boto3 (`sagemaker` client)
- IAM execution roles — scoped permissions for AWS services (not users),
  trust policies, SageMaker as a principal
- S3 as the artifact store (first encounter in this learning path)
- Cost comparison across the three modes for the same workload
- When managed inference is the right call vs rolling your own fleet

## Interview talking points this project earns me

- "When would you use SageMaker over EC2 + ALB + ASG?" — trade-off framing
- The three deployment modes and when each fits (interactive user traffic
  vs spiky batch vs offline scoring)
- Cold-start behavior of SageMaker Serverless and how it compares to Lambda
- Why `inference.py` has four separate handlers (separation of concerns:
  parse / load / predict / serialize)
- The `model.tar.gz` + S3 artifact pattern and how it maps to real
  production ML workflows (CI builds artifact, uploads to S3, triggers
  endpoint update)
- Comparing cost: a `ml.m5.large` real-time endpoint at ~$0.115/hour vs
  equivalent self-managed `m5.large` EC2 at ~$0.096/hour — the ~20%
  premium for SageMaker's managed layer

## Files (as they get written)

- `train.py` — unchanged from Project 2.5 (produces `model.pkl`)
- `inference.py` — the four SageMaker handler functions
- `package_model.sh` — tar `model.pkl` + `inference.py` into `model.tar.gz`
- `deploy_realtime.py` — SageMaker SDK script to deploy the real-time endpoint
- `deploy_serverless.py` — same model, serverless configuration
- `batch_transform.py` — one-off batch job driver
- `invoke_endpoint.py` — test invocations via SDK, boto3, and CLI examples
- `batch_input.csv` — sample feature rows for batch transform
- `model.tar.gz` — gitignored (build artifact)

## Not in this project

- **Training in SageMaker.** We reuse Project 2's local `train.py`. SageMaker
  Training jobs are a separate feature; focus here is deployment.
- **Multi-model endpoints.** SageMaker supports hosting many models behind
  one endpoint; skipped — single-model is clearer for a first encounter.
- **Shadow / A-B testing.** SageMaker has production variants for canarying;
  skipped as advanced feature.
- **Model monitoring (Model Monitor).** Data-drift detection, feature-skew
  alerts — real but out of scope for a first-encounter deployment project.
- **SageMaker Studio IDE.** The web-based notebook environment; we use local
  Python + the SDK instead for cleaner reproducibility.
- **Custom container (BYOC).** Prebuilt sklearn container is sufficient for
  Iris. BYOC becomes essential for models not covered by prebuilt images
  (custom frameworks, special runtime deps) — out of scope here.