"""
LSEG session management.

Open strategy (tried in order):
  1. ld.open_session() with no arguments — works when LSEG Workspace is running
     locally and has a valid platform session. This is the normal desktop case.
  2. ld.open_session(app_key=...) — used when LSEG_APP_KEY is set in the
     environment, for headless / server environments without Workspace.

The smoke test (2026-04-21) confirmed that strategy 1 works in this environment.
Strategy 2 is kept as a documented fallback.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Generator

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def open_session() -> None:
    """Open a LSEG data session.

    Tries the local Workspace session first (no credentials required).
    Falls back to LSEG_APP_KEY if the first attempt fails.

    Raises RuntimeError if both strategies fail or lseg-data is not installed.
    """
    try:
        import lseg.data as ld  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "lseg-data is not installed. Run: pip install lseg-data"
        ) from exc

    # Strategy 1: local Workspace session (confirmed working in this environment)
    try:
        ld.open_session()
        logger.info("LSEG session opened via local Workspace configuration.")
        return
    except Exception as workspace_exc:
        logger.debug("Workspace open failed (%s) — trying APP_KEY fallback.", workspace_exc)

    # Strategy 2: explicit app key (headless / server mode)
    app_key = os.environ.get("LSEG_APP_KEY", "").strip()
    if not app_key:
        raise RuntimeError(
            "Could not open LSEG session via Workspace and LSEG_APP_KEY is not set.\n"
            "Either start LSEG Workspace or set LSEG_APP_KEY in your .env file."
        )
    try:
        ld.open_session(app_key=app_key)
        logger.info("LSEG session opened via LSEG_APP_KEY.")
    except Exception as key_exc:
        raise RuntimeError(
            f"Both session strategies failed.\n"
            f"  Workspace error: {workspace_exc}\n"
            f"  APP_KEY error:   {key_exc}"
        ) from key_exc


def close_session() -> None:
    """Close the active LSEG data session."""
    try:
        import lseg.data as ld  # type: ignore
        ld.close_session()
        logger.info("LSEG session closed.")
    except Exception as exc:
        logger.warning("Error closing LSEG session (non-fatal): %s", exc)


def is_session_open() -> bool:
    """Return True if a LSEG session appears to be active."""
    try:
        import lseg.data as ld  # type: ignore
        return ld.get_default_session() is not None
    except Exception:
        return False


@contextmanager
def managed_session() -> Generator[None, None, None]:
    """Context manager that opens a session on entry and closes on exit.

    Usage::

        with managed_session():
            df = ld.get_history("LCOc1", fields=["TRDPRC_1"], start="2025-01-01", end="2025-12-31")
    """
    open_session()
    try:
        yield
    finally:
        close_session()
