"""Session authentication for opt-in HTTP workflow checks.

Use a dedicated existing test account. Credentials are never command-line flags,
printed, or written to disk; the temporary session is revoked when the check ends.
"""
from __future__ import annotations

import getpass
import os
import sys
import warnings
from collections.abc import Iterator
from contextlib import contextmanager

import httpx


class CheckAuthenticationError(RuntimeError):
    """A workflow check could not establish or close its authenticated session."""


def _credentials() -> tuple[str, str]:
    username = os.environ.get("NUTRICHAT_CHECK_USERNAME", "").strip()
    if not username:
        raise CheckAuthenticationError(
            "Set NUTRICHAT_CHECK_USERNAME to an existing dedicated test account. "
            "The check does not register accounts automatically."
        )
    password = os.environ.get("NUTRICHAT_CHECK_PASSWORD")
    if not password:
        if not sys.stdin.isatty():
            raise CheckAuthenticationError(
                "Set NUTRICHAT_CHECK_PASSWORD for a non-interactive check, or run in "
                "a terminal to enter the password securely."
            )
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            try:
                password = getpass.getpass("NutriChat check account password: ")
            except (getpass.GetPassWarning, EOFError) as exc:
                raise CheckAuthenticationError(
                    "A secure password prompt is unavailable; use "
                    "NUTRICHAT_CHECK_PASSWORD instead."
                ) from exc
    if not password:
        raise CheckAuthenticationError("The check account password must not be empty.")
    return username, password


@contextmanager
def authenticated_client(base_url: str, *, timeout: float = 20) -> Iterator[httpx.Client]:
    """Log in, yield one cookie-preserving client, and revoke its session afterward."""
    username, password = _credentials()
    with httpx.Client(
        base_url=base_url,
        timeout=timeout,
        headers={"X-NutriChat-Request": "1"},
    ) as client:
        try:
            response = client.post("/auth/login", json={"username": username, "password": password})
        except httpx.HTTPError as exc:
            raise CheckAuthenticationError(
                "Could not connect to the NutriChat login endpoint. Check --base-url "
                "and that the API is running."
            ) from exc
        finally:
            password = ""
        if response.status_code != 200:
            raise CheckAuthenticationError(
                f"NutriChat login failed (HTTP {response.status_code}). Verify the existing "
                "check account credentials and server availability."
            )
        failed = False
        try:
            yield client
        except BaseException:
            failed = True
            raise
        finally:
            cleanup_error = None
            try:
                response = client.post("/auth/logout")
                if response.status_code not in (204, 401):
                    cleanup_error = f"HTTP {response.status_code}"
            except httpx.HTTPError:
                cleanup_error = "connection failed"
            if cleanup_error:
                text = f"Could not revoke the workflow check session ({cleanup_error})."
                if failed:
                    print("WARNING: " + text, file=sys.stderr)
                else:
                    raise CheckAuthenticationError(text)
