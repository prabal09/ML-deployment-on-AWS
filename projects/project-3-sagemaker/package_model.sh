#!/bin/bash
# ---------------------------------------------------------------------------
# package_model.sh — bundle model.pkl + inference.py into model.tar.gz
# for upload to S3 and consumption by a SageMaker prebuilt sklearn container.
#
# Expected tarball structure (SageMaker convention):
#   model.tar.gz
#   ├── model.pkl
#   └── code/
#       └── inference.py
# ---------------------------------------------------------------------------
set -euo pipefail

if [ ! -f "model.pkl" ]; then
    echo "ERROR: model.pkl not found. Run 'python train.py' first." >&2
    exit 1
fi

if [ ! -f "inference.py" ]; then
    echo "ERROR: inference.py not found." >&2
    exit 1
fi

# Stage the code/ subdirectory (SageMaker's convention for custom handlers).
mkdir -p code
cp inference.py code/

# Create the tarball. Deterministic order so content hash is reproducible.
tar -czvf model.tar.gz model.pkl code/inference.py

# Clean up staging.
rm -rf code

echo ""
echo "Created model.tar.gz:"
tar -tzvf model.tar.gz