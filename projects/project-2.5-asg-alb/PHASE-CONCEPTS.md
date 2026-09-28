# Project 2.5 — Phase Concepts

Reference doc for the concepts introduced across Phases A–E of Project 2.5.
Each phase gets its own section of "what interviewers would ask" questions,
with answers and short one-liners suitable for repeating in an interview.

Phases A (user-data.sh) and B (/health endpoint) are omitted — they're
small enough that the code itself is the concept.

---

## Phase C — ACM Certificate + DNS Validation

### 1. What's a CNAME, and how does it differ from an A record and an Alias record?

Three DNS record types you'll encounter in this project:

| Type | Maps | Example |
|---|---|---|
| **A** | Hostname → IPv4 address | `iris.ml-prabal.com` → `18.227.219.211` |
| **CNAME** | Hostname → another hostname | `www.example.com` → `example.com` |
| **Alias** (Route 53-only) | Hostname → AWS resource | `iris-scaled.ml-prabal.com` → ALB DNS name |

**Why the distinctions matter:**

- **CNAMEs can't sit at the "zone apex"** (the naked domain like `ml-prabal.com`
  with no subdomain). This is a DNS spec limitation. If you want the apex domain
  to point at an ALB, you need an **Alias record** — it's Route 53's workaround.
- **Alias records are free.** Route 53 doesn't bill DNS queries against Alias
  records to AWS resources. Regular A/CNAME queries cost $0.40 per million.
  Negligible for small sites, real at scale.
- **Alias records auto-track underlying IPs.** ALBs have multiple backing IPs
  that rotate. An Alias record follows those changes automatically. A CNAME to
  the ALB's DNS name would also work but doesn't get the free-queries benefit.

**Interview one-liner:** *"A records give hostnames IPs. CNAMEs give hostnames
aliases to other hostnames. Route 53 Aliases give AWS resources first-class
hostname support — free queries, apex-domain support, auto-tracking of
underlying IPs."*

### 2. Why does ACM validate ownership via a CNAME instead of email or an HTTP challenge?

ACM offers two validation methods: **DNS validation via CNAME** and **email
validation**. DNS is the recommended one.

**What the CNAME proves:** only someone with authority over a domain's DNS zone
can add records to it. Placing a specific ACM-provided value at a specific
ACM-chosen hostname under your domain proves you control DNS, which is
functionally equivalent to owning the domain.

**Why CNAME specifically:** consistent format (name → value pair), doesn't
conflict with normal domain records, easy to leave in place indefinitely.

**The auto-renewal advantage:** the CNAME stays in your zone forever. Every
~11 months, ACM re-checks it as part of renewal. If it's still there, the cert
renews automatically. **Zero human involvement, forever.** This is the *real*
reason DNS validation is recommended over email — email validation requires a
human to click a link every renewal cycle, which people forget.

**Interview one-liner:** *"DNS validation proves domain control by asking me to
write a specific value into my zone. Once written, that same record enables
truly automatic cert renewal forever — no manual step ever again."*

### 3. What does "In use" mean for an ACM certificate, and why is renewal eligibility tied to it?

"In use" = cert is currently attached to at least one AWS service (ALB,
CloudFront, API Gateway, etc.).

**Why renewal eligibility depends on it:** renewing a certificate involves real
work at the CA layer (issuing a fresh cert, validating the CNAME, etc.). ACM
would rather not spend that effort on certs nobody attached to anything.
Attaching a cert to a live AWS resource signals "this cert is worth
renewing" — flip to `Eligible`. Detaching flips back to `Ineligible`.

**Practical observation you saw firsthand:**
- Phase C: cert issued but not yet attached → `In use: No`, `Renewal eligibility: Ineligible`.
- Phase E: ALB listener attached to the cert → `In use: Yes`, `Renewal eligibility: Eligible`.

**Consequence for real ops:** if you tear down the ALB and forget to reattach
the cert to something else, renewal stops. Eventually the cert expires. Not
catastrophic on a personal domain; important to know for production.

**Interview one-liner:** *"ACM only auto-renews certs that are attached to
something. Attaching flips the eligibility switch on; detaching flips it off. A
cheap way to auto-cull unused certs from the renewal pipeline."*

### 4. Why is ACM region-scoped, and why is CloudFront the exception?

ACM certificates are stored in a specific AWS region because ACM itself is a
**regional service** (like most AWS services — EC2, ALB, RDS, S3 buckets).
A cert issued in `us-east-2` can only be attached to AWS resources in
`us-east-2`.

**CloudFront is the exception** because it's a **global** service — a CDN with
edge locations worldwide, not tied to any one region. AWS decided that
CloudFront's certs must all live in `us-east-1` (Northern Virginia, AWS's
historical flagship region), regardless of where the rest of your
infrastructure lives.

**Practical:** if your ALB is in `us-east-2` and you also have a CloudFront
distribution in front of it, you need **two ACM certs** for the same domain —
one in `us-east-2` for the ALB, one in `us-east-1` for CloudFront. Both are
free; just don't get confused about the region selector.

**Interview one-liner:** *"ACM is regional like most AWS services. CloudFront
is global and requires its certs in us-east-1 — a historical quirk you'd only
trip on if you're using multiple TLS-terminating services."*

---

## Phase D — Launch Template + user-data + Tags

### 1. Launch Template vs Launch Configuration — what changed and why?

**Launch Configuration (LC)** — the older, deprecated resource type for
describing "how to launch an instance." Immutable: once created, you can't
edit it. Change something → create a new LC → update the ASG to point at the
new one.

**Launch Template (LT)** — the modern replacement, launched ~2018 and made the
strong default around 2020. Key improvements:
- **Versioning built in** — every edit creates a new version (v1, v2, v3…).
  The template itself remembers its own history.
- **Edit-in-place** — you don't create a new resource for every change.
- **Supports modern instance features** — T-instance unlimited mode, dedicated
  hosts, capacity reservations, Nitro-specific settings, instance metadata
  service v2 configuration.
- **Referenced by version** — ASGs can point at `$Default`, `$Latest`, or a
  specific version number. Great for controlled rollouts: create v2, test it
  by attaching a single ASG to v2, only promote v2 to `$Default` after verify.

**AWS's official stance:** new deployments should use Launch Templates.
Launch Configurations are deprecated and will eventually stop supporting new
instance types.

**Interview one-liner:** *"Launch Templates replaced Launch Configurations
around 2020 — versioning, edit-in-place, and support for modern instance
features. LC is deprecated; use LT for anything new."*

### 2. Why leave the subnet blank in the LT, and what happens if you set it?

**If you set a subnet in the LT:** every instance the LT stamps out lands in
that specific subnet. Subnets are per-AZ, so this pins all instances to one
Availability Zone.

**Why that's bad for ASG use:** the whole point of the ASG (Phase F) is to
spread instances across multiple AZs for HA. If AZ `us-east-2a` has an outage,
you want instances in `us-east-2b` and `us-east-2c` still serving traffic.
Locking the LT to one subnet defeats this.

**How ASG handles it if the LT has a subnet:** the ASG's own multi-AZ
configuration overrides the LT's subnet setting per launch. Works, but
confusing — the LT looks like it says one thing while the ASG does another.
Cleanest is to just not set the subnet in the LT at all.

**Rule of thumb:** the LT owns "what the instance looks like" (AMI, size, keys,
SG, user data). The ASG owns "where and how many" (subnets, AZs, capacity).
Keep the concerns separate.

**Interview one-liner:** *"LT sets what the instance looks like; ASG sets where
it goes. Subnet is a where-decision — belongs in the ASG, not the LT."*

### 3. What's cloud-init, and why does user-data only run on first boot?

**Cloud-init** is a Linux service that runs at boot time on virtually every
cloud instance. Its job: apply cloud-provider-supplied initialization (SSH
keys, hostname, user data scripts, cloud-config directives). Present in every
mainstream Linux distro's cloud image — Ubuntu, Amazon Linux, RHEL, Debian.

**The "user-data runs once" mechanism:**
- On first boot, cloud-init reads the user-data field from AWS's instance
  metadata service, executes it, then writes a state marker to
  `/var/lib/cloud/instance/`.
- On every subsequent boot, cloud-init sees the marker and **skips user-data
  execution.**
- Rationale: user-data is meant as a first-boot bootstrap. Rerunning it could
  destroy state — reinstalling packages, resetting configs, wiping data.

**To force re-execution** (very useful during script development):
```bash
sudo cloud-init clean          # deletes the state marker + old logs
sudo reboot                    # or: sudo cloud-init init
```
Next boot re-runs user-data as if the instance were brand new.

**For scripts that should run on every boot** (not just first): use a
`systemd` service or `/etc/rc.local`, not user-data.

**Interview one-liner:** *"Cloud-init is the standard Linux first-boot service.
It runs user-data exactly once and marks the instance as initialized.
Persistent state means safe boots; iterating requires `cloud-init clean`."*

### 4. Why the specific bash flags and logging pattern in `user-data.sh`?

The two "prologue" lines of `user-data.sh` deserve individual explanation:

**`set -euxo pipefail`** — inverts bash's dangerous defaults:
- **`-e`** = exit immediately on any command failure. Without this, a failed
  `apt-get install` (or any other step) would let the script continue with
  broken state and appear to succeed.
- **`-u`** = exit if any variable is referenced but never set. Catches typos
  like `$REPO_DIRR` where `$REPO_DIR` was meant.
- **`-x`** = print each command before executing it. Makes debugging trivial
  — the log shows exactly what ran.
- **`-o pipefail`** = if any command in a pipeline fails, the whole pipeline
  fails. Without this, `foo | bar` returns bar's exit code and silently hides
  foo's failure.

These four together turn bash from "fail silent, continue with garbage" into
"fail loud, exit immediately." Standard hardening for any production script.

**`exec > >(tee /var/log/user-data.log) 2>&1`** — persistent structured
logging:
- Redirects both stdout (`>`) and stderr (`2>&1`) to a `tee` process.
- `tee` writes to two destinations: (a) the current terminal (which cloud-init
  captures into `/var/log/cloud-init-output.log`), and (b) a persistent file
  at `/var/log/user-data.log`.
- Why the second copy: cloud-init's log rotates. Your own log at a known,
  documented path survives rotations, log-cleanup jobs, etc.

**Post-boot debugging becomes trivial:** SSH in, `sudo cat /var/log/user-data.log`,
see the exact sequence of commands and their output. If something failed, the
last visible command is where.

**Interview one-liner:** *"Bash's default is ignore-errors-and-keep-going.
`set -euxo pipefail` inverts that. The `tee` line ensures the boot log
survives even if cloud-init's default logs are rotated away."*

### 5. Why tag with Key/Value (Environment=dev, Project=iris-scaled) instead of one descriptive tag?

Tags are the primary dimension AWS uses for **grouping and filtering
resources**. AWS Cost Explorer, Config, Resource Groups, IAM policies, and
third-party tools (Datadog, CloudHealth, etc.) all group resources by tag
**key**, then filter by tag **value**.

**If you tag with a single "descriptive" tag** like `Name="iris-scaled-dev"`,
you've collapsed multiple dimensions into one string. You can only group by
that exact tag key. Cost Explorer can't answer:
- "Show me all `dev`-environment spend, regardless of project"
- "Show me all `iris-scaled` spend, regardless of environment"
- "Break down `iris-scaled` spend by environment"

**If you tag with `Environment=dev` and `Project=iris-scaled` as two separate
tags,** each becomes an independent dimension:
- Group by `Environment` key → dev/staging/prod breakdown across all projects.
- Group by `Project` key → per-project breakdown across all environments.
- Filter by both → dev spend for iris-scaled specifically.

**Convention:** the Key is a **category** ("what dimension am I tagging?").
The Value is the **specific answer** for that resource ("what value along that
dimension?"). Two categories → two tags.

**Standard tag keys in most orgs:** `Environment`, `Project`, `Owner`,
`CostCenter`, `ManagedBy`. Adopting the same set across every resource makes
governance and cost allocation infinitely easier.

**Interview one-liner:** *"Tag keys are dimensions; tag values are the specific
answer for that dimension. Cost tools group by key. One-string tags collapse
all dimensions into one, losing the reporting power."*

---

## Phase E — Target Group + ALB + HTTPS Listener

### 1. Target group vs ALB — why are they separate resources?

**The intuition:** feels redundant. Doesn't the ALB already know where to
send traffic?

**The answer:** they solve different problems and change on different
timescales.

- **ALB** = the public entry point. Owns: public DNS name, TLS cert, listener
  ports (80/443), rules for *which requests to accept and where to route them*.
- **Target group** = a dynamic pool of backend endpoints. Owns: the list of
  instances currently receiving traffic, the health check configuration, and
  the "how to talk to backends" details (protocol, port).

**Why separate — different lifecycles:**
- The ALB is provisioned once and lives for months/years.
- The target group's *membership* churns every minute — ASG adds instances
  during scale-up, removes them during scale-down, replaces unhealthy ones.
- One ALB can route to *many* target groups (URL rules, blue/green
  deployments, `/api/v1` vs `/api/v2`).
- One target group can be shared across multiple ALBs.

**Interview one-liner:** *"The ALB decides whether to accept a request. The
target group decides where to send it. Different concerns, different lifecycles,
different resources."*

### 2. The three security groups — why not one?

Three SGs across the account after Project 2.5 setup:

| SG | Attached to | Inbound |
|---|---|---|
| `launch-wizard-4` | Project 2's single EC2 | SSH from your IP, HTTP 80 from anywhere, HTTPS 443 from anywhere |
| `iris-scaled-instance-sg` | Project 2.5 fleet instances | SSH from your IP, HTTP 80 from `iris-scaled-alb-sg` |
| `iris-scaled-alb-sg` | Project 2.5 ALB | HTTPS 443 from anywhere, HTTP 80 from anywhere |

**Why separate:**

- **Isolation across projects** — Project 2 and 2.5 are independent systems.
  Sharing an SG would mean rule changes for one project affect the other.
- **Isolation across roles** — the ALB and the fleet play *different roles*.
  The ALB is the public front door (must accept internet traffic on 443). The
  fleet is behind that door (should only accept traffic from the door).
  Different roles → different minimum privileges → different SGs.

**What breaks if you merged the instance SG + ALB SG:**

- If instance SG allowed 443 from anywhere: fleet instances become publicly
  reachable on 443, but they don't listen there (nginx is only on 80). No
  functional break, but a wasted rule widening the attack surface.
- If instance SG allowed 80 from `0.0.0.0/0` instead of from the ALB SG:
  **anyone scanning AWS IPv4 ranges could bypass the ALB and hit your fleet
  instances directly.** Your `/predict` endpoint would be reachable without the
  ALB in the loop — bypassing any future rate limiting, WAF rules, or auth you
  add at the ALB layer.

**Interview one-liner:** *"One SG per role. Each SG's rules describe the
minimum access that role needs. Merging SGs creates over-privileged rules
by default."*

**Bonus — security group chaining:** your `iris-scaled-instance-sg` rule for
HTTP 80 uses the ALB SG's *ID* as the source, not an IP range. AWS resolves
this at packet-inspection time: "is the source IP one of the IPs currently
used by an ENI attached to `iris-scaled-alb-sg`?" This means: as the ALB
scales or changes underlying IPs, the rule keeps working with zero config
change. **Interview-worthy because IP-based rules break when the referenced
resource's IPs change.**

### 3. Health checks — two independent actors (three, once ASG joins)

Two separate health-check systems supervise your fleet:

**`systemd`** (on each instance, from Phase D):
- Watches the gunicorn process from *inside* the box.
- If gunicorn crashes → systemd restarts it within 3 seconds
  (`Restart=always`).
- Blind to network / HTTP / anything outside the process itself.

**ALB target group health check** (from Phase E):
- Watches the endpoint from *outside* the box (from the ALB's perspective).
- Every 30 seconds, ALB sends `GET /health` to each registered instance on
  port 80.
- If 2 consecutive checks fail → ALB marks that instance "unhealthy" → stops
  routing traffic to it, but leaves it registered.
- If checks recover → ALB marks it "healthy" → resumes routing.
- **Doesn't restart anything.** It just steers traffic away.

**How they interact in real failure scenarios:**

| Failure | systemd's response | Target group's response |
|---|---|---|
| gunicorn process crashes | Restarts it in 3s | Sees 502 for ~30s while systemd restarts, marks unhealthy after 2 failed checks, stops sending traffic. Once gunicorn is back, checks pass, traffic resumes. |
| Model file corrupted → gunicorn refuses to start | Retries; eventually gives up after `StartLimitBurst` failures | Instance perpetually unhealthy, no traffic ever routed to it. |
| Instance box unreachable (network partition) | N/A — systemd is on the box, which is unreachable | Health check timeouts, mark unhealthy, no traffic. |
| Instance terminated entirely | N/A | Unhealthy → in Phase F, ASG's own health check notices → **ASG launches a replacement instance**. |

**Three levels, three responders** (once ASG joins in Phase F):

```
Level        Watched by       Responds by
-----        ----------       -----------
Process      systemd          Restart process
Service      ALB target grp   Divert traffic
Instance     ASG              Replace instance
```

**Interview one-liner:** *"systemd knows if my process is running. The target
group knows if my endpoint answers. The ASG knows if my instance is alive.
Three levels, three responders, three timescales."*

### 4. Why TLS terminates at the ALB, not on each instance

Project 2 had certbot on the box; Project 2.5 has ACM at the ALB. Three
concrete reasons:

**1. Cert lifecycle vs instance lifecycle.**
In Project 2, the cert's renewal state (certbot timer, `/etc/letsencrypt/`)
lived on the specific instance. If that instance dies, the cert renewal state
dies with it. In an ASG world where instances are ephemeral (average lifetime:
hours to weeks), that model is fundamentally broken. ACM cert on the ALB is
decoupled from any instance's lifetime.

**2. Compute cost.**
TLS handshake is CPU-expensive (~5–30 ms per new connection). At 100 req/s
across 5 instances:
- **TLS at instance:** each of 5 instances handles ~20 handshakes/sec →
  each burns some CPU on encryption.
- **TLS at ALB:** ALB (which has dedicated TLS hardware and offloading)
  handles all handshakes → instances receive plain HTTP and spend 100% of
  their CPU on your actual app (sklearn inference).

**3. Operational simplicity.**
One cert to manage vs N. One cert to renew vs N. One place to see cert expiry
vs N.

**What we give up:**
Traffic between ALB and instance is plaintext (over the AWS internal network).
If an attacker breaches the VPC and can sniff internal traffic, they see
cleartext HTTP. Standard mitigation: rely on VPC network isolation (private
subnets, no route from public internet to instance private IPs). Advanced
mitigation: run TLS on the ALB→instance leg too ("end-to-end encryption"),
but this reintroduces per-instance cert management.

**Interview one-liner:** *"TLS at the edge. Instances are ephemeral; certs are
long-lived. Coupling them means you either can't scale down cleanly or can't
rotate the cert atomically."*

### 5. The 17-step request trace

Trace one HTTPS request from your laptop to a `/predict` response. Every
step names a resource decision made explicitly during Project 2.5:

```text
1.  Client: browser fetches https://iris-scaled.ml-prabal.com/health
2.  Client OS: DNS resolver queries; eventually hits Route 53
3.  Route 53: alias record iris-scaled.ml-prabal.com → ALB DNS name → ALB IPs
    (added in Phase G)
4.  Client: opens TCP connection to ALB's public IP on port 443
5.  ALB: TLS handshake using ACM cert for iris-scaled.ml-prabal.com — encrypted
    channel established
6.  ALB: decrypts, sees "GET /health, Host: iris-scaled.ml-prabal.com"
7.  ALB listener rule: default action → forward to target group iris-scaled-tg
8.  ALB: picks a healthy registered target (one of N ASG instances, round-robin)
9.  ALB: opens plain HTTP to instance's private IP:80
10. Instance security group iris-scaled-instance-sg: source is ALB SG → accept
11. nginx on instance: matches server_name (or default), enters location /
12. nginx: proxy_pass http://127.0.0.1:8000
13. gunicorn (managed by systemd): assigns request to an available worker
14. Worker: Flask routes to health_check(), returns {"status":"healthy"}, 200
15. gunicorn → nginx → ALB (each on plain HTTP internally)
16. ALB: re-encrypts response over TLS
17. Client: receives 200 OK with {"status":"healthy"}
```

**Every one of the 17 steps is a resource or configuration decision made
explicitly:** Route 53 for step 3, ACM for step 5, target group + registration
for steps 7–8, security groups for step 10, nginx config for step 11,
gunicorn config for step 13, Flask app for step 14, and so on.

If someone asks *"walk me through how a request flows through your
architecture,"* rehearse this list. Practicing it out loud once is worth an
hour of reading.