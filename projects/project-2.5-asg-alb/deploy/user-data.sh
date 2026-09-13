#!/bin/bash
set -euxo pipefail
exec > >(tee /var/log/user-data.log) 2>&1

# ---------------------------------------------------------------------------
# Project 2.5 — first-boot bootstrap.
# Runs as root via cloud-init on Ubuntu 24.04 when a fresh instance launches
# from the Launch Template. Must be idempotent (safe to rerun).
# Total run time: ~2-3 minutes on t2.micro.
# ---------------------------------------------------------------------------

REPO_URL="https://github.com/prabal09/ML-deployment-on-AWS.git"
REPO_DIR="/home/ubuntu/ML-deployment-on-AWS"
APP_DIR="${REPO_DIR}/projects/project-2.5-asg-alb"

# 1. System packages
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3.12-venv python3-pip nginx git

# 2. Clone repo + set up app (as the ubuntu user, so paths and ownership are right)
sudo -u ubuntu -H bash <<EOF
set -euxo pipefail
if [ ! -d "${REPO_DIR}" ]; then
    git clone "${REPO_URL}" "${REPO_DIR}"
else
    cd "${REPO_DIR}" && git pull
fi

cd "${APP_DIR}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python train.py
EOF

# 3. systemd unit
cp "${APP_DIR}/deploy/iris-api.service" /etc/systemd/system/iris-api.service
systemctl daemon-reload
systemctl enable --now iris-api

# 4. nginx site
cp "${APP_DIR}/deploy/nginx.conf" /etc/nginx/sites-available/iris-api
ln -sf /etc/nginx/sites-available/iris-api /etc/nginx/sites-enabled/iris-api
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "Bootstrap complete: $(date -u)"


# Section	                                            Purpose
# set -euxo pipefail	                                e=exit on error, u=exit on unbound var, x=print each command (for debug), o pipefail=fail on pipe errors. Standard bash "fail loud" pattern.
# exec > >(tee /var/log/user-data.log) 2>&1	            Everything written to stdout/stderr goes both to the terminal (cloud-init log) AND to /var/log/user-data.log. Makes post-boot debugging trivial: SSH in, cat /var/log/user-data.log.
# DEBIAN_FRONTEND=noninteractive	                    Prevents apt from prompting for input during install. On an unattended boot, any prompt would hang the script forever.
# sudo -u ubuntu -H bash <<EOF ... EOF	                The heredoc runs as the ubuntu user (correct owner for ~/ML-deployment-on-AWS/). -H sets HOME=/home/ubuntu. Then the script returns to root for system-level steps.
# if [ ! -d ... ]; then git clone; else git pull; fi	Idempotency: re-running the script doesn't error on "directory already exists."
# systemctl enable --now iris-api	                    The --now shortcut does enable + start in one call.
# ln -sf and rm -f	                                    -f (force) makes both commands succeed whether the target exists or not — idempotent.