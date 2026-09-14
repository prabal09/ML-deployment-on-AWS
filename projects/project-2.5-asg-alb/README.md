# Project 2.5 — Launch Template + Auto Scaling Group + ALB

Taking the single hand-built EC2 instance from Project 2 and turning it into a
self-healing, self-scaling fleet behind a load balancer. Same Iris classifier,
same Flask + Gunicorn + nginx stack — but now reproducible from zero and
horizontally scalable.

**Status:** ready to start — Project 2 complete (2026-09-13); single-instance HTTPS endpoint live at `https://iris.ml-prabal.com/predict`

## Goal

Replace the "pet" server from Project 2 with "cattle": a fleet of identical
EC2 instances that the Auto Scaling Group keeps alive and resizes on demand,
fronted by an Application Load Balancer that terminates TLS and spreads traffic.
No instance is special — any one can die and be replaced with no downtime,
and the endpoint stays reachable at `https://iris.ml-prabal.com/predict`.

The point of this project is to learn what "highly available" and "scalable"
actually cost to build by hand, before Projects 5–6 (ECS/EKS) hide it again.

## Architecture

```
Client (curl / browser)
        │  HTTPS
        ▼
   Route 53 (DNS)
        │   alias record → ALB DNS name (no fixed IP anymore)
        ▼
   Application Load Balancer   :443   (TLS terminates HERE, via ACM cert)
        │   forwards :80 to healthy targets
        ├───────────────┬───────────────┐
        ▼               ▼               ▼
     EC2 #1          EC2 #2          EC2 #3        ◄── Auto Scaling Group
     nginx :80       nginx :80       nginx :80        keeps desired count
     gunicorn :8000  gunicorn :8000  gunicorn :8000   healthy, replaces
     Flask + model   Flask + model   Flask + model    dead instances
        └──────── all stamped from one Launch Template ────────┘
```

Key changes vs. Project 2:

- **TLS moves to the ALB.** ACM certificate on the load balancer instead of
  certbot on the box. Instances serve plain HTTP internally; no cert renewal
  cron to babysit.
- **Route 53 points at the ALB, not an IP.** Instance IPs are now ephemeral —
  an alias record targets the ALB's stable DNS name.
- **Instances are disposable.** Whatever was done by hand in Project 2 (deps,
  code, systemd unit, nginx config) is now scripted so a blank instance
  configures itself on first boot.

## Prerequisites

- **Project 2 finished through Phase G** — a working single-instance HTTPS
  endpoint whose setup steps you can reproduce
- The Project 2 `deploy/` artifacts (`myapp.service`, `nginx.conf`) — reused
  verbatim here
- A domain in Route 53 (the ALB alias record needs a hosted zone)
- An AWS account with quota for a small EC2 fleet, an ALB, and ACM

## The one thing that makes this project work

Every instance must go from **blank → serving with zero manual steps**. Two
ways to achieve that; this project uses user data first, then optionally bakes
an AMI:

| Approach | How | Trade-off |
|----------|-----|-----------|
| **User data script** | Launch Template runs a boot script that installs deps, pulls code, drops in the systemd/nginx files, starts the service | Slower boot, but change code without rebuilding an image |
| **Golden AMI** | Snapshot a fully-configured instance; Launch Template boots straight from it | Fast boot, but rebuild the AMI on every code change |

## Deployment plan

| Phase | What | Where |
|-------|------|-------|
| A | Refactor Project 2 setup into a single idempotent bootstrap script (no manual SSH) | Reuse `deploy/` |
| B | Add a `/health` endpoint to the Flask app for the target group | `app.py` |
| C | Request an ACM certificate for `iris.<my-domain>` (DNS validation) | AWS console |
| D | Create the Launch Template — AMI, instance type, security group, user-data script | AWS console / CLI |
| E | Create the ALB + target group + HTTPS listener (443 → target group, using the ACM cert) | AWS console / CLI |
| F | Create the ASG from the launch template, attach to the target group, set min/max/desired (2/4/2) | AWS console / CLI |
| G | Repoint Route 53 from the old EC2 IP to an alias record → the ALB | AWS console |
| H | Add a target-tracking scaling policy (CPU 50%); test self-healing and scale-out | — |

## What I'm learning here

- Launch Templates and reproducible instance provisioning (user data vs. AMI)
- Auto Scaling Groups — desired/min/max, health checks, instance replacement
- Application Load Balancers — listeners, target groups, health checks
- **ALB health checks vs. ASG health checks** — who decides "unhealthy" and
  who decides "replace"
- TLS termination at the load balancer with ACM (vs. certbot on the box)
- Route 53 alias records to an ALB (why you can't use an A-record to an IP)
- **Stateless instances** — why every instance must be interchangeable
- Horizontal vs. vertical scaling — the pattern that reappears in ECS and EKS

## Interview talking points this project earns me

- Why a load balancer needs a health check, and what endpoint it should hit
- The difference between ALB and ASG health checks and how they interact
- Why instances must be stateless for autoscaling to work
- Where to terminate TLS and why the edge is the standard answer
- How ALB + target groups here map 1:1 onto ECS services (Project 5) and
  Kubernetes Ingress/Services (Project 6)

## Files (as they get written)

- `deploy/user-data.sh` — first-boot bootstrap: installs deps, pulls code,
  installs the systemd/nginx files, starts the service
- `deploy/iris-api.service` — systemd unit (copied from Project 2)
- `deploy/nginx.conf` — nginx site config, HTTP-only now (copied from Project 2; certbot lines dropped since TLS moves to ALB)
- `launch-template.json` — Launch Template definition (for CLI reproducibility)
- `asg-config.json` — ASG settings (min/max/desired, health check config)
- `NOTES.md` — console click-paths and gotchas as I go

## Not in this project

- Containers — Project 4 (Lambda+ECR) is where Docker starts
- Managed autoscaling — Projects 5 (ECS) and 6 (EKS) hand this off to
  orchestrators; this project is the by-hand version so I understand what
  they automate
- Multi-region / blue-green deploys — out of scope; single region, rolling
  instance replacement only
