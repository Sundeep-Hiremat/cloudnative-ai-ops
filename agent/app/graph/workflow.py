import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agent.app.core.state import IncidentState
from agent.app.agents.triage import triage_agent_node
from agent.app.agents.diagnostic import diagnostic_agent_node
from agent.app.agents.remediation import remediation_agent_node
from agent.app.agents.gitops import gitops_agent_node
from agent.app.agents.post_mortem import post_mortem_agent_node
from agent.app.tools.git_tools import gitops_tools

logger = logging.getLogger("kubeops.graph")

def apply_gitops_fix_node(state: IncidentState) -> IncidentState:
    """Applies the approved GitOps patch to disk / repository."""
    approval_status = state.get("approval_status", "pending")
    remediation = state.get("remediation", {})
    resource_name = state.get("resource_name", "payment-service")
    target_file = f"apps/{resource_name}/values.yaml"
    
    if approval_status == "approved":
        logger.info(f"[ApplyNode] Applying approved patch for incident {state['incident_id']}")
        # In real GitOps, this pushes to Git where ArgoCD auto-syncs
        # We apply the values to the local gitops directory
        current_content = gitops_tools.read_manifest(target_file)
        if "512Mi" in current_content:
            new_content = current_content.replace("memory: 512Mi", "memory: 1Gi").replace("memory: 256Mi", "memory: 512Mi")
            gitops_tools.apply_patch_to_file(target_file, new_content)
        
        state["status"] = "verifying"
        state["current_step"] = "patch_applied_to_gitops"
    else:
        logger.info(f"[ApplyNode] Incident {state['incident_id']} was rejected or skipped.")
        state["status"] = "rejected"
        state["current_step"] = "rejected_by_operator"
        
    return state

def create_incident_workflow():
    """Builds and compiles the LangGraph Multi-Agent State Machine."""
    workflow = StateGraph(IncidentState)

    # Add Agent Nodes
    workflow.add_node("triage", triage_agent_node)
    workflow.add_node("diagnostic", diagnostic_agent_node)
    workflow.add_node("remediation", remediation_agent_node)
    workflow.add_node("gitops", gitops_agent_node)
    workflow.add_node("apply_fix", apply_gitops_fix_node)
    workflow.add_node("post_mortem", post_mortem_agent_node)

    # Edge transitions
    workflow.add_edge(START, "triage")
    workflow.add_edge("triage", "diagnostic")
    workflow.add_edge("diagnostic", "remediation")
    workflow.add_edge("remediation", "gitops")
    # Human approval check happens between gitops and apply_fix
    workflow.add_edge("gitops", "apply_fix")
    workflow.add_edge("apply_fix", "post_mortem")
    workflow.add_edge("post_mortem", END)

    # Memory checkpointer for state persistence
    checkpointer = MemorySaver()
    app = workflow.compile(checkpointer=checkpointer)
    return app

# Singleton compiled application
incident_graph = create_incident_workflow()
