# NutriChat on a cloud VM with Qwen

The cloud option uses a Linux VM with Docker Compose, PostgreSQL, API, worker and
internal AI service. Qwen inference runs in Alibaba Cloud Model Studio; no GPU is
needed on the VM. This is a single-user prototype, accessed privately by SSH tunnel
by default. An optional HTTPS reverse proxy supports a password-protected public
demo. Multi-user data isolation and managed database provisioning are not implemented.

## Configure Qwen

Use the API key, OpenAI-compatible base URL and model available in the **same**
Model Studio region/workspace. See the official
[structured output documentation](https://www.alibabacloud.com/help/en/model-studio/qwen-structured-output).
Copy the base URL ending in `/compatible-mode/v1`, without `/chat/completions`.
The adapter uses Chat Completions JSON output with thinking disabled; select a model
that supports these parameters. `qwen-plus` is the configurable default.

For local Qwen mode, add to your existing `.env` (do not overwrite existing settings):

```dotenv
NUTRITION_PROVIDER=qwen
DASHSCOPE_API_KEY=your-secret-key
QWEN_BASE_URL=your-workspace-compatible-base-url
QWEN_MODEL=qwen-plus
QWEN_TIMEOUT_SECONDS=12
WORKER_REQUEST_TIMEOUT_SECONDS=20
```

Then run `docker compose up -d --build`. API and AI must use the same provider mode.
With `NUTRITION_PROVIDER=demo`, no API key is needed and a strict English parser is used.
In Qwen mode, food text is sent to Model Studio. The result must contain supported
food names and positive explicit gram weights. Unknown items or invalid responses
fail the job; there is no fabricated fallback estimate. LLM extraction can still
misinterpret input, so users review the saved interpreted meal before confirming.
Nutrition numbers come from the demo catalogue, not the model.

## Deploy a private cloud demo

1. Provision a Linux VM and install Docker with Compose. Copy this repository there.
2. Create a private `.env` on the VM containing `DASHSCOPE_API_KEY`, `QWEN_BASE_URL`,
   optional `QWEN_MODEL`, and `POSTGRES_PASSWORD`. Use a long random alphanumeric
   database password (it is interpolated into a connection URL). Do not commit it.
3. Run from the repository root:

   ```sh
   docker compose -f compose.cloud.yaml up -d --build
   docker compose -f compose.cloud.yaml ps
   ```

4. From your own computer open an SSH tunnel (replace `user@your-vm`):

   ```sh
   ssh -L 8080:127.0.0.1:8000 user@your-vm
   ```

5. Open `http://localhost:8080/app`. Submit `100克鸡蛋` in Qwen mode, wait for the
   estimate, verify the interpreted meal, correct it to `200克鸡蛋`, then confirm.
   Reload the page to verify persistence.

Only the API binds a loopback port; DB and AI have no published ports. Restrict
inbound VM traffic to SSH from your own IP. The cloud Compose file is standalone:
use `-f compose.cloud.yaml` for all cloud commands rather than combining it with
local `compose.yaml`. It uses a separate persistent database volume.

## Operation and recovery

- Logs: `docker compose -f compose.cloud.yaml logs --tail=100 api worker ai`
- Back up before upgrades:
  `docker compose -f compose.cloud.yaml exec -T db pg_dump -U nutrichat nutrichat > backup.sql`
- Deploy updates: `docker compose -f compose.cloud.yaml up -d --build`
- Stop without removing data: `docker compose -f compose.cloud.yaml down`
- Do not use `down -v` unless intentionally deleting the database.

Migrations run before the API starts; the worker waits for API health. Qwen's timeout
must be shorter than the worker HTTP timeout. Failed estimates can be corrected and
resubmitted. Automatic retries and recovery of jobs interrupted while claimed are
not yet implemented. Keep one worker for the demo. Cloud infrastructure and real
Qwen credentials have not been exercised by the repository's mocked tests.

## Check configuration before enabling Qwen

From the project root, run a local configuration check (does not call Qwen):

```sh
docker compose run --rm --no-deps api python scripts/check_qwen.py
```

After supplying a valid key and matching region/workspace base URL, verify one
synthetic Chinese meal through the real Qwen API (may incur model usage charges):

```sh
docker compose run --rm --no-deps api python scripts/check_qwen.py --live
```

The check does not print credentials. Once it passes, set `NUTRITION_PROVIDER=qwen`,
recreate the services with `docker compose up -d --build`, and test the UI. The
repository's mocked Qwen tests verify routing and error propagation; they do not
establish that an account has model access or that its region configuration is correct.

## Optional public demo with an IP address

Use `compose.cloud.yaml` together with `compose.public.yaml`. Only the reverse
proxy publishes ports 80 and 443. The API remains on loopback port 8000; the
database and AI service remain internal. Allow inbound TCP 80 and 443 in the
VM security group. Do not publish database or AI ports.

Runtime files live in the git-ignored `deploy/public/` directory: `nginx.conf`,
`auth.env`, `acme/`, and `letsencrypt/`. Restrict this directory to the operator.
Generate a unique strong password. The private `auth.env` supplies `DEMO_USERNAME`,
`DEMO_PASSWORD_HASH` (hex salt plus colon plus scrypt digest, n=16384/r=8/p=1/dklen=32),
`DEMO_SESSION_KEY` (a random signing secret of at least 32 characters), and
`DEMO_PUBLIC_ORIGIN` (the exact HTTPS origin). Share
the password only with intended demo users; this is one shared account, not
separate user accounts or private per-user histories.

Start with an HTTP configuration that serves only `/.well-known/acme-challenge/`
from `/var/www/acme` and returns 503 elsewhere. Request the certificate using:

```sh
docker run --rm \
  -v /opt/nutrichat/deploy/public/letsencrypt:/etc/letsencrypt \
  -v /opt/nutrichat/deploy/public/acme:/var/www/acme \
  certbot/certbot:v5.4.0 certonly --non-interactive --agree-tos \
  --register-unsafely-without-email --preferred-profile shortlived \
  --webroot --webroot-path /var/www/acme \
  --ip-address YOUR_PUBLIC_IP --cert-name nutrichat
```

Review the certificate authority's subscriber agreement before registering.
Replace `__PUBLIC_IP__` in `deploy/nginx-public.conf.template`, save it as the
runtime `nginx.conf`, validate with `nginx -t`, then reload the proxy. It redirects
HTTP to HTTPS and uses `/login` for a normal HTML login form. The gateway validates
a signed, Secure/HttpOnly/SameSite=Strict cookie for application requests; sessions
expire after 8 hours. The gateway is internal and has no published port. A
POST to `/logout` clears the session cookie. Rotate `DEMO_SESSION_KEY` and recreate
the gateway to invalidate every existing session. `/metrics` is
blocked externally. Request size and per-IP request rate are bounded.

IP certificates expire after approximately six days. Install
`scripts/renew-public-certificate.sh` as a systemd oneshot service with a timer
running twice daily. The script renews when due and reloads Nginx. Check the timer
and journal regularly; this setup has no external renewal-failure notification.
Use Certbot `renew --dry-run` to verify the renewal path.

Verify from outside the VM: HTTP redirects, HTTPS has a trusted certificate,
unauthenticated application requests redirect to `/login`, incorrect form passwords
return 401 without a browser authentication challenge, authenticated `/app`
returns 200, and the estimate/correct/confirm flow succeeds. Keep the public
ports closed if TLS or authentication cannot be verified.

To remove public access without deleting meal data:
`docker compose -f compose.cloud.yaml -f compose.public.yaml stop proxy`,
then remove the website rules from the security group.
