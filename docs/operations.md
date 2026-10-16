# Operations Notes

## Local startup

1. copy `.env.example` to `.env`
2. run `docker compose up --build`
3. open `http://localhost:8000/app`
4. submit a supported meal with gram weights
5. review, correct if needed, and confirm the estimate

For Qwen and a cloud VM, see [cloud deployment](cloud-deployment.md).

## Health endpoints

- API live: `/health/live`
- API ready: `/health/ready`
- AI live: `/health/live`
- AI ready: `/health/ready`

## Metrics

- API metrics: `/metrics`
- AI metrics: `/metrics`
- Prometheus: enable the `observability` profile

## Common useful commands

- run tests: `pytest -q`
- run smoke tests: `SMOKE_BASE_URL=http://localhost:8000 pytest tests/smoke -q`
- run migrations: `docker compose run --rm api alembic upgrade head`
- seed demo data: `docker compose run --rm api python scripts/seed_demo_data.py`

## Failure handling in the starter

If AI processing fails:

- the job is marked failed
- the case is marked failed
- the error is recorded on the job row

## Resetting local state

To remove local database state:

- `docker compose down -v --remove-orphans`


## Chinese nutrition dialogue extension

See [nutrition data and dialogue](nutrition-data.md) for the current catalogue,
`needs_input` state, revision-checked reply API, provenance and deployment checks.
Migration `20261016_0004` adds JSON conversation/draft/questions/details and a user-facing
error field. Existing records remain readable; no tables or meal records are removed.
