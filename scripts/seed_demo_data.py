from __future__ import annotations

import argparse
import os

from sqlalchemy import select

from services.common.db import get_session_factory
from services.common.models import Case, CaseStatus, Job, JobStatus, User

DEMO_CASES = [
    {
        "title": "Cannot login to operations portal",
        "description": (
            "User reports password reset did not restore access to the "
            "operations dashboard."
        ),
    },
    {
        "title": "Invoice charge looks incorrect",
        "description": (
            "Customer believes this month includes an unexpected duplicate "
            "billing charge."
        ),
    },
    {
        "title": "Production service outage alert",
        "description": "Several users report the service is down and requests are failing.",
    },
]


def main(username: str) -> None:
    username = username.strip().lower()
    if not username:
        raise ValueError("Specify an existing owner with --username or NUTRICHAT_SEED_USERNAME.")
    session_factory = get_session_factory()

    with session_factory() as db:
        user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if user is None:
            raise ValueError("The specified account does not exist. Create it before seeding.")
        for item in DEMO_CASES:
            case = Case(
                user_id=user.id,
                title=item["title"],
                description=item["description"],
                status=CaseStatus.QUEUED.value,
            )
            db.add(case)
            db.flush()

            db.add(
                Job(
                    case_id=case.id,
                    status=JobStatus.PENDING.value,
                )
            )

        db.commit()

    print(f"Seeded {len(DEMO_CASES)} demo cases.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic cases for an existing account.")
    parser.add_argument("--username", default=os.environ.get("NUTRICHAT_SEED_USERNAME", ""),
                        help="Existing account that owns the demo cases (not a password).")
    args = parser.parse_args()
    try:
        main(args.username)
    except ValueError as exc:
        parser.error(str(exc))
