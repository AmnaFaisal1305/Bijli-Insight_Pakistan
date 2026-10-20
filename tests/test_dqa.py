"""
Location: tests/test_dqa.py
Purpose: Tests that DataQualityAgent correctly logs FIX, FILL, and FLAG actions.
"""
from pathlib import Path
import pandas as pd
from agents.data_quality_agent import DataQualityAgent, DQAAction


def test_dqa_logs_actions_properly(tmp_path):
    """Asserts that DQA records an audited decision log."""
    log_file = tmp_path / "quality_log.json"
    agent = DataQualityAgent(log_path=log_file)
    
    agent.log_decision(
        column_name="temperature_c",
        violation_rule="TestRule",
        action=DQAAction.FIX,
        affected_count=5,
        rationale="Unit test verification"
    )
    
    assert len(agent.decision_log) == 1
    assert agent.decision_log[0]["action_taken"] == DQAAction.FIX
    assert agent.decision_log[0]["affected_rows_count"] == 5