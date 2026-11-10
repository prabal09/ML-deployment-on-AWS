# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Base image: AWS-published Lambda base image for Python 3.12.
#
# This image:
#   - Includes Python 3.12 pre-installed at /var/lang/bin/python3.12
#   - Includes the Lambda Runtime Interface Client (RIC) as the ENTRYPOINT
#   - Expects your code at /var/task  (available via ${LAMBDA_TASK_ROOT})
#   - When run on Lambda (or via the Runtime Interface Emulator), the RIC
#     listens for invocation requests and calls the handler specified by CMD.
# ---------------------------------------------------------------------------
FROM public.ecr.aws/lambda/python:3.12

# Install Python dependencies into the Lambda task directory.
# Copy requirements.txt first so pip install is cached when only the app
# code changes (same layer-caching principle from Phase A).
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt \
    --target ${LAMBDA_TASK_ROOT}

# Copy application code and model artifact.
COPY app.py model.pkl ${LAMBDA_TASK_ROOT}/

# Tell Lambda which function to invoke on each event.
# Format: "<module>.<attribute>"
# Here: app.py's `handler` object (our Mangum wrapper around the FastAPI app).
CMD ["app.handler"]