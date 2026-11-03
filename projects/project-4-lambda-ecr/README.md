# Project 4 — Lambda + ECR + FastAPI (Serverless Containers)

Deploying the Iris classifier as an AWS Lambda function packaged as a Docker
container image stored in ECR, with a FastAPI app inside and API Gateway in
front providing public HTTPS access. First real encounter with containers
(Docker from scratch), with FastAPI (not just Flask), with ECR (private
Docker registry), and with Lambda's container runtime (not plain Zip packages).

**Status:** not started

## Goal

Take the same `train.py` + `model.pkl` from previous projects and deliver a
production-shaped serverless ML endpoint:

- Reachable at `https://<your-api-gateway>/predict` over HTTPS.
- Running on-demand (zero cost when idle, scales to thousands of concurrent
  invocations automatically).
- Built, tested, and deployed via a Docker image lifecycle you own
  end-to-end: local build → ECR push → Lambda update.
- Written in FastAPI with pydantic request validation and auto-generated
  Swagger UI at `/docs`.

The point: internalize the container deploy loop AND the serverless Lambda
model AND the FastAPI framework, all in one project. These three concepts
reappear separately across Projects 5 (ECS) and 6 (EKS) — Project 4 is
where you learn them together, in the simplest possible packaging.

## Architecture

```
Client (browser / curl / mobile)
       │  HTTPS
       ▼
   API Gateway REST API    (public HTTPS endpoint, request validation, throttling)
       │
       │ Lambda invoke (SigV4-signed internally)
       ▼
   AWS Lambda Function     (serverless compute; billed per invocation)
       │  reads container image from ECR at cold start
       ▼
   Docker Container Image  (your packaged app)
       │
       ▼
   FastAPI app
       │  via Mangum (ASGI → Lambda event adapter)
       ▼
   /predict route  ────►  sklearn model.predict()
```

**All owned by you:** the Dockerfile, the FastAPI code, the ECR image tags,
the Lambda function config, the API Gateway route.

**Owned by AWS:** the compute instances running your container (Lambda's
Firecracker VMs), the HTTPS termination at API Gateway, the ECR storage.

## Key changes vs Project 3 (SageMaker)

| | Project 3 (SageMaker) | Project 4 (Lambda + ECR) |
|---|---|---|
| **Container** | AWS-provided prebuilt sklearn container | You write the Dockerfile from scratch |
| **Container runtime** | SageMaker's managed serving layer | AWS Lambda's container runtime |
| **Web framework** | None — SageMaker provides the serving layer | You write it — FastAPI with Mangum |
| **Deploy mechanism** | SageMaker SDK (`model.deploy()`) | `docker push` to ECR + Lambda update |
| **Cost model** | Hourly instance billing (real-time) | Per invocation + GB-seconds (true serverless) |
| **Public access** | SigV4-authenticated endpoint URL | API Gateway with public HTTPS |
| **Framework version coupling** | Container controls numpy/sklearn versions | You control everything in Dockerfile |

**The biggest conceptual shift:** you own the container top-to-bottom. In
SageMaker you supplied `inference.py` and AWS provided everything else. In
Project 4 you supply the Dockerfile, the Python runtime, the pip
dependencies, the web framework, the handler, and the model loading
code — AWS provides the Lambda execution environment and ECR storage.

## The one thing that makes this project work

**AWS Lambda's container image deployment** — introduced in late 2020.
Instead of Lambda functions as zip files of Python code (traditional), Lambda
can execute any Docker image that:
- Is based on an AWS-provided Lambda runtime base image (`public.ecr.aws/lambda/python:3.12`)
- Has a `CMD` pointing at an exported handler function (`app.handler`)
- Is ≤10 GB uncompressed

The handler function is called by Lambda on every invocation. For a FastAPI
app, that handler is a `Mangum` instance that adapts Lambda events to ASGI
calls:

```python
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI()

@app.post("/predict")
def predict(...): ...

handler = Mangum(app)   # <-- Lambda calls this per invocation
```

Mangum translates Lambda's `event`/`context` into HTTP requests FastAPI
understands, and translates FastAPI's HTTP responses back into Lambda's
expected JSON output. ~500 lines of Python; no magic.

## Prerequisites

- **Docker Desktop installed and running** on Windows — this is the biggest
  new piece. Verify with `docker version` returning both Client + Server
  info.
- `model.pkl` reused from Project 3 (same numpy 1.x + sklearn 1.2 pins; a
  model trained for the sklearn SageMaker container works perfectly in a
  Lambda container as long as the Dockerfile installs matching versions).
- AWS CLI configured (unchanged from previous projects).
- Python environment for local FastAPI testing. We'll create a dedicated
  venv for Project 4.

## Deployment plan

| Phase | What | Where |
|-------|------|-------|
| A | Install Docker; learn Dockerfile basics; build a trivial Python image to internalize the mechanics | Local |
| B | Rewrite the app in FastAPI; add `/predict` + `/health` + pydantic validation; test with uvicorn locally | Local |
| C | Rewrite Dockerfile against the AWS Lambda Python base image; add Mangum; build and test with the local Lambda emulator (RIE) | Local |
| D | Create an ECR repository; authenticate Docker to ECR; tag and push the image | AWS CLI + Docker |
| E | Create an IAM execution role for Lambda; create the Lambda function pointing at the ECR image; test via Lambda console | AWS Console |
| F | Create an API Gateway REST API with `/predict` route; integrate with Lambda; deploy to a stage; test from `curl` | AWS Console |
| G | (Optional) Point `iris-lambda.ml-prabal.com` at the API Gateway via Route 53 + ACM | AWS Console |
| H | Teardown + cost retrospective | — |

## What I'm learning here

- **Docker from scratch** — writing a Dockerfile line by line, understanding
  layers and image caching, choosing a base image, `COPY` vs `ADD`,
  `CMD` vs `ENTRYPOINT`, build-time vs run-time environment
- **FastAPI** — route decorators, pydantic input validation, dependency
  injection, auto-generated OpenAPI docs at `/docs`
- **Mangum** — the ASGI ↔ Lambda event adapter; why ASGI matters for
  async-capable frameworks
- **AWS Lambda container runtime** — distinct from zip-based deploys;
  10 GB image limit, 15 min invocation timeout, ephemeral `/tmp`
- **ECR** — AWS's private Docker registry; `aws ecr get-login-password`
  authentication pattern; image tag conventions
- **API Gateway** — REST APIs vs HTTP APIs (we use REST); Lambda proxy
  integration; stages; deployment lifecycle
- **Cold starts in Lambda containers** — larger than zip-based (image pull
  overhead); provisioned concurrency as the mitigation
- **Why containers for Lambda** — the specific use cases that justify the
  cold-start penalty vs zip deploys

## Interview talking points this project earns me

- *"When would you choose Lambda container images over zip-based Lambda?"*
  — Models >50 MB can't fit in zip Lambda layers; container images handle
  the Iris model (~115 KB), a 500 MB BERT, and a 2 GB transformer equally
  well up to 10 GB.
- *"Why FastAPI inside Lambda instead of writing a plain Lambda handler?"* —
  pydantic validation at the framework level, Swagger UI for free, async
  support if you ever need it, same code portable to ECS/EKS without
  rewrites.
- *"Explain the request path from client to prediction."* — the 10-step
  trace (API Gateway → Lambda invoke → container cold start if needed →
  Mangum adapter → FastAPI route → model.predict).
- *"What's the cost model difference between Lambda and SageMaker real-time?"*
  — Lambda bills per invocation + GB-sec of compute; idle = $0. SageMaker
  real-time bills per instance-hour continuously. For <100K
  requests/month, Lambda is dramatically cheaper. For >10M, SageMaker's
  flat rate wins.
- *"Compared to Projects 2 and 2.5 — what did Lambda+Docker remove, what
  did it add?"* — removed: nginx, gunicorn, systemd, EC2 management, ASG,
  ALB, certbot, OS patching. Added: Dockerfile authorship, ECR lifecycle,
  Lambda invocation model, Mangum adapter, API Gateway configuration.

## Files (as they get written)

- `train.py` — reused unchanged
- `app.py` — FastAPI rewrite with `/predict` and `/health`
- `requirements.txt` — numpy, scikit-learn, fastapi, mangum
- `Dockerfile` — Lambda-base-image-derived container
- `.dockerignore` — exclude venv, __pycache__, model.pkl
- `build_push.sh` — build image, authenticate ECR, tag, push
- `test_local.sh` — run container with Lambda RIE for local testing
- `requirements.txt` — pinned exact versions matching Lambda base image

## Not in this project

- **Zip-based Lambda** — the simpler/older deployment style. Container
  images are a superset of capabilities and worth learning first.
- **Lambda layers** — a packaging mechanism for dependencies with zip
  Lambda; irrelevant with container images.
- **Provisioned concurrency** — a cold-start mitigation that keeps N
  Lambda instances warm. Costs money even when idle; defeats the "pay
  nothing when idle" selling point for a learning project. Advanced
  feature.
- **Lambda SnapStart** — only applies to Java runtime; not usable here.
- **CloudFront in front of API Gateway** — adds caching + geographic
  distribution. Overkill for a single-region demo.
- **AWS SAM / CDK / Terraform** — infra-as-code tools for Lambda. We'll
  use raw AWS CLI + Console to understand the primitives. IaC in a
  dedicated project would be its own learning track.
- **Testing with pytest / unit tests** — standard Python testing, not
  AWS-specific. Important for real projects, out of scope here.