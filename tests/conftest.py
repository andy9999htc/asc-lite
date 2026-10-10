"""Shared pytest fixtures for async helper execution."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any

import pytest


@pytest.fixture(name="asyncio_run")
def fixture_asyncio_run():
    """Run a coroutine to completion inside tests without pytest-asyncio."""

    def _run(coro: Awaitable[Any]) -> Any:
        return asyncio.run(coro)

    return _run
