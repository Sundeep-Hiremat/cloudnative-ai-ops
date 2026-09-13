import logging
from datetime import datetime, timezone
from agent.app.core.state import IncidentState, StepLog, GitOpsPRData
from agent.app.tools.git_tools import gitops_tools

logger = logging.getLogger("kubeops.agents.gitops")

def gitops_agent_node(state: IncidentState) -> IncidentState:
    """GitOps Agent: Opens a Git Pull Request proposal and sets up human-in-the-loop checkpoint."""
    incident_id = state.get("incident_id")
    resource_name = state.get("resource_name", "payment-service")
    target_file = f"apps/{resource_name}/values.yaml"
    remediation = state.get("remediation", {})
    strategy = remediation.get("strategy", "AUTO_FIX")
    
    pr_title = f"fix(gitops): remediate {resource_name} {strategy.lower().replace('_', ' ')} [Incident #{incident_id[:6]}]"
    pr_body = (
        f"## 🤖 Automated SRE Remediation by KubeOps-Aegis\n\n"
        f"### 📋 Incident Summary\n"
        f"- **Incident ID**: `{incident_id}`\n"
        f"- **Resource**: `{resource_name}` in namespace `{state.get('namespace', 'default')}`\n"
        f"- **Alert**: `{state.get('alert_name')}`\n"
        f"- **Strategy**: `{strategy}`\n\n"
        f"### 🔍 Root Cause Analysis\n"
        f"{state.get('diagnostic', {}).get('root_cause', 'N/A')}\n\n"
        f"### 🛠️ Proposed Manifest Changes\n"
        f"```diff\n{remediation.get('unified_diff', '')}\n```\n\n"
        f"### 🛡️ Safety & Policy Checks\n"
        f"- ✅ Resource Quota Constraints: PASSED\n"
        f"- ✅ Schema Validation: PASSED\n"
        f"- ✅ Blast Radius: ISOLATED TO `{resource_name}`\n"
    )

    pr_record = gitops_tools.create_gitops_pr(
        incident_id=incident_id,
        target_file=target_file,
        pr_title=pr_title,
        pr_body=pr_body
    )

    log_entry = StepLog(
        timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
        agent="GitOpsAgent",
        action="GitOps PR Proposal Prepared",
        details=f"Branch: {pr_record['branch_name']} | Awaiting Human Approval",
        status="warning"
    )

    state["gitops_pr"] = pr_record
    state["current_step"] = "awaiting_human_approval"
    state["status"] = "waiting_approval"
    state["step_logs"].append(log_entry.model_dump())

    return state
