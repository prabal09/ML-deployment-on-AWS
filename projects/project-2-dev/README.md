# Project 2 — EC2 + Flask + Gunicorn + nginx + systemd + Route53

Deploying an Iris classifier as an HTTPS ML endpoint on a single EC2 instance,
managed as a proper Linux service and fronted by a reverse proxy.

**Status:** in progress — Phase A (local Flask + Gunicorn setup)

## Goal

Take a trained scikit-learn model and expose it as a JSON prediction API,
reachable at `https://iris.<my-domain>/predict`, running on a single Ubuntu
EC2 instance. No Docker, no managed services — this project is about
learning what those managed services hide.

## Architecture

```
Client (curl / browser)
        │  HTTPS
        ▼
   Route 53 (DNS)
        │
        ▼
   EC2 (Ubuntu 24.04)
        ├── nginx        :80 / :443   (reverse proxy, TLS termination)
        └── gunicorn     127.0.0.1:8000   (WSGI server, 3 workers)
            └── Flask app
                └── model.pkl (sklearn Iris classifier)
        managed by systemd (auto-restart, boot-start)
```

## Prerequisites

- Python 3.11+
- An AWS account with a free-tier-eligible EC2 quota
- A domain name in Route 53 (or willingness to skip TLS and use the raw
  EC2 public IP)

## Local development (Phase A)

```bash
python -m venv venv
source venv/bin/activate         # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
python train.py                  # produces model.pkl
python app.py                    # dev server, http://127.0.0.1:5000
```

## Deployment plan

| Phase | What | Where |
|-------|------|-------|
| A | Flask app + Gunicorn local test | Windows laptop |
| B | Launch EC2, install deps | EC2 |
| C | Deploy code, sanity-check with Gunicorn | EC2 |
| D | Wrap Gunicorn in a systemd service | EC2 |
| E | Put nginx in front | EC2 |
| F | Point Route 53 at EC2 public IP | AWS console |
| G | Add HTTPS via Let's Encrypt / certbot | EC2 |

## What I'm learning here

- Flask project layout from an empty folder
- WSGI (why the dev server isn't production)
- Gunicorn worker model
- systemd service files and `journalctl`
- nginx as a reverse proxy
- DNS records and TLS termination
- The full request path a real ML endpoint travels

## Files (as they get written)

- `train.py` — trains and saves `model.pkl`
- `app.py` — Flask app with `/predict` endpoint
- `requirements.txt` — pinned Python deps
- `deploy/myapp.service` — systemd unit file
- `deploy/nginx.conf` — nginx site config
- `model.pkl` — trained artifact (gitignored)

## Not in this project

- Docker — Project 4 (Lambda+ECR) is where containers start
- Autoscaling — Project 2.5 will convert this instance into a Launch
  Template + ASG behind an ALB
- Managed inference — Project 3 (SageMaker) covers that path
