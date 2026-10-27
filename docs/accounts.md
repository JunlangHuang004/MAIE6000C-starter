# Independent accounts (experimental `test` branch)

This increment adds username/password registration, login, logout, expiring sessions
and account-owned meal histories. The `test` branch now also includes
[private profiles and daily references](personalization.md). Daily weight logs,
monthly trends and Google login are not implemented.
The original branches and the `w07-midterm` submission snapshot remain unchanged.
No public ECS deployment is included in this increment.

## Preview alongside the existing application

From the `test` checkout, with Docker and a recent Docker Compose installed:

```sh
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml up -d --build
```

Open <http://localhost:8001/app>, register an account, and submit `100g egg`.
Review and confirm the result, sign out, then register another account. The second
account has a separate meal history. Sign back into the first to restore its meals.
Use the same hostname throughout: `localhost` and `127.0.0.1` are different origins.

This preview uses the offline demo parser and a separate database volume. It does
not use Qwen credentials or provide the full Chinese estimation workflow. It does
not stop or replace the application on port 8000. To stop it without deleting data:

```sh
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml down
```

## Account and session contract

- Usernames are case-insensitive ASCII letters, digits and underscores, 3–32
  characters. Passwords are 10–128 characters and preserve whitespace.
- Each account has a stable internal UUID, independent of the username and suitable
  for future external identity bindings. No email address is collected.
- Passwords use scrypt with a random per-password salt. Sessions use random opaque
  tokens; only the SHA-256 token digest is saved in PostgreSQL. Passwords and session
  tokens are never stored in browser localStorage.
- Sessions expire after eight hours. Logout revokes the current session in the
  database and clears its cookie. Cookies are HttpOnly and SameSite=Strict; use
  Secure cookies for every public deployment.
- Mutations require `X-NutriChat-Request: 1`. When an `Origin` header is present it
  must exactly match `AUTH_PUBLIC_ORIGIN`. Cross-origin browser access is not enabled.
- Every meal, case and linked job is authorized against the authenticated account.
  Foreign and ownerless records return 404. Requests without a session return 401;
  opening `/app` without a session redirects to `/login`.
- The UI saves the last meal ID under a user-specific localStorage key, clears
  sensitive content on logout/session expiry, and lists only that account's meals.

## Configuration

| Variable | Application default | Purpose |
| --- | --- | --- |
| `AUTH_PUBLIC_ORIGIN` | `http://localhost:8000` | Exact browser origin, including scheme and non-default port |
| `AUTH_COOKIE_SECURE` | `true` | Send the session cookie only over HTTPS |
| `AUTH_REGISTRATION_ENABLED` | `false` | Allow new accounts through `/auth/register` |

The local `.env.example` explicitly enables registration and allows HTTP cookies.
An existing private `.env` needs these settings added deliberately; preserve its
other settings and secrets. Public cloud Compose requires an explicit origin and
defaults to Secure cookies with registration closed. Enable registration only when
you intend to accept new accounts, then close it if the demo is limited to a group.
Existing accounts can still log in when registration is disabled.

The public proxy template now forwards login and auth routes to the API. The old
shared gateway is no longer used by `compose.public.yaml`. Existing runtime Nginx
configuration must be updated along with the application before a future deployment.
See [cloud deployment](cloud-deployment.md) for migration and configuration details.

## Existing data and recovery limits

Migration `0006` creates users and sessions and adds nullable owner IDs to analyses
and cases. Existing records are retained with no owner and cannot be read through
user-facing endpoints. The previous shared login is not converted into an account,
and old meals are not assigned to the first person who registers. Any later import
needs a separately reviewed ownership mapping and a database backup.

This learning prototype has no self-service password reset, email verification,
account deletion UI, account merge, MFA or Google OAuth. Password recovery and
session administration need an operator workflow before wider use. Authentication
rate limiting is bounded but in-process; it resets on restart and is not shared
across API replicas. The proxy also limits requests; behind one proxy the API's
IP bucket may be shared by clients. Use one API process for this preview.

PostgreSQL backups now contain password hashes and private meal histories; keep
them outside Git and restrict access. The worker and AI service remain internal
trusted services. Queue retries, crash recovery and request idempotency are still
separate future work.

## Verification

Build the preview, then run:

```sh
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml run --rm --no-deps api \
  pytest -q tests/unit tests/integration
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml run --rm --no-deps api ruff check .
docker compose -p nutrichat-accounts --env-file .env.example \
  -f compose.yaml -f compose.accounts.yaml exec -T \
  -e SMOKE_BASE_URL=http://api:8000 api pytest -q tests/smoke
```

Smoke checks create synthetic accounts and meals in this disposable preview. They
require registration to be open or explicit smoke account credentials. Unit and
integration tests cover session expiry/revocation, CSRF checks, registration,
password hashing and cross-account access on all record operations. These checks
do not establish Qwen accuracy or the security of an untested public deployment.
