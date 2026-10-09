"""Tests for the M3 decision logging helper."""

from __future__ import annotations

import logging

from custom_components.asc_lite.engine.types import Decision
from custom_components.asc_lite.logging import log_decision


def test_log_decision_records_rule_id_reason_and_result(caplog) -> None:
    logger = logging.getLogger("asc_lite.test")
    decision = Decision(
        rule_id="R-ASTRO-001",
        reason_code="ASTRO_EVENING_CLOSE",
        target_position=0,
    )

    with caplog.at_level(logging.INFO, logger=logger.name):
        log_decision(logger, "cover.terrace", "sun_elevation", decision, result="selected")

    assert "cover.terrace" in caplog.text
    assert "R-ASTRO-001" in caplog.text
    assert "ASTRO_EVENING_CLOSE" in caplog.text
    assert "selected" in caplog.text
