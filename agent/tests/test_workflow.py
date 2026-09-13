import pytest
from agent.app.core.state import IncidentState
from agent.app.agents.triage import triage_agent_node
from agent.app.agents.diagnostic import diagnostic_agent_node
from agent.app.agents.remediation import remediation_agent_node
from agent.app.agents.gitops import gitops_agent_node
from agent.app.agents.post_mortem import post_mortem_agent_node

@pytest.fixture
def mock_incident_state() -> IncidentState:
    return {
        "incident_id": "test-inc-12345",
        "alert_name": "KubeContainerOOMKilled",
        "namespace": "default",
        "resource_kind": "Deployment",
        "resource_name": "payment-service",
        "labels": {"app": "payment-service"},
        "annotations": {"description": "Memory limit exceeded"},
        "raw_alert": {},
        "current_step": "init",
        "step_logs": [],
        "triage": None,
        "diagnostic": None,
        "remediation": None,
        "gitops_pr": None,
        "approval_status": "pending",
        "approval_comment": None,
        "verification": None,
        "post_mortem": None,
        "status": "triaging",
        "error": None
    }

def test_triage_node(mock_incident_state):
    state = triage_agent_node(mock_incident_state)
    assert state["triage"] is not None
    assert state["triage"]["category"] == "ResourceExhaustion"
    assert state["triage"]["severity"] == "CRITICAL"
    assert state["status"] == "diagnosing"
    assert len(state["step_logs"]) == 1

def test_diagnostic_node(mock_incident_state):
    state = triage_agent_node(mock_incident_state)
    state = diagnostic_agent_node(state)
    assert state["diagnostic"] is not None
    assert state["diagnostic"]["confidence_score"] >= 0.9
    assert "OOM" in state["diagnostic"]["root_cause"]
    assert state["status"] == "remediating"

def test_remediation_node(mock_incident_state):
    state = triage_agent_node(mock_incident_state)
    state = diagnostic_agent_node(state)
    state = remediation_agent_node(state)
    assert state["remediation"] is not None
    assert state["remediation"]["strategy"] == "RESOURCE_BUMP"
    assert "1Gi" in state["remediation"]["unified_diff"]
    assert state["status"] == "waiting_approval"

def test_gitops_and_post_mortem_node(mock_incident_state):
    state = triage_agent_node(mock_incident_state)
    state = diagnostic_agent_node(state)
    state = remediation_agent_node(state)
    state = gitops_agent_node(state)
    assert state["gitops_pr"] is not None
    assert "kubeops-fix" in state["gitops_pr"]["branch_name"]

    state["approval_status"] = "approved"
    state = post_mortem_agent_node(state)
    assert state["status"] == "resolved"
    assert state["verification"]["status"] == "VERIFIED_HEALTHY"
    assert "Post-Mortem" in state["post_mortem"]
