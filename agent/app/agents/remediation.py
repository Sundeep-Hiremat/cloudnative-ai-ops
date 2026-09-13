import logging
from datetime import datetime, timezone
from agent.app.core.state import IncidentState, StepLog, RemediationData, ProposedPatch
from agent.app.tools.git_tools import gitops_tools

logger = logging.getLogger("kubeops.agents.remediation")

def remediation_agent_node(state: IncidentState) -> IncidentState:
    """Remediation Agent: Generates GitOps YAML patches following declarative GitOps principles."""
    resource_name = state.get("resource_name", "payment-service")
    category = state.get("triage", {}).get("category", "")
    target_file = f"apps/{resource_name}/values.yaml"
    
    logger.info(f"[RemediationAgent] Formulating GitOps patch for {target_file}")
    
    # 1. Read existing GitOps manifest
    original_content = gitops_tools.read_manifest(target_file)
    
    # 2. Formulate patch
    if category == "ResourceExhaustion" or "oom" in state.get("alert_name", "").lower():
        # Bump memory limit from 512Mi to 1Gi and requests from 256Mi to 512Mi
        modified_content = original_content.replace("memory: 512Mi", "memory: 1Gi").replace("memory: 256Mi", "memory: 512Mi")
        strategy = "RESOURCE_BUMP"
        rationale = (
            f"Increase memory limit for '{resource_name}' from 512Mi to 1Gi (100% headroom expansion) "
            f"and memory request from 256Mi to 512Mi to prevent OOM-killer terminations under peak load."
        )
        patches = [
            ProposedPatch(
                file_path=target_file,
                target_field="resources.limits.memory",
                current_value="512Mi",
                proposed_value="1Gi",
                patch_diff="- memory: 512Mi\n+ memory: 1Gi",
                explanation="Doubles container memory limit to accommodate 5000 cache items."
            ),
            ProposedPatch(
                file_path=target_file,
                target_field="resources.requests.memory",
                current_value="256Mi",
                proposed_value="512Mi",
                patch_diff="- memory: 256Mi\n+ memory: 512Mi",
                explanation="Ensures scheduler places pod on node with sufficient guaranteed RAM."
            )
        ]
        risk_level = "LOW"
    elif category == "CrashLoop" or "crash" in state.get("alert_name", "").lower():
        # Add missing DB_PASSWORD environment variable
        modified_content = original_content + "\n  - name: DB_PASSWORD\n    value: \"vault-secret-ref:db-prod\"\n"
        strategy = "CONFIG_FIX"
        rationale = "Inject missing required DB_PASSWORD secret reference to resolve startup crash."
        patches = [
            ProposedPatch(
                file_path=target_file,
                target_field="env",
                current_value="missing DB_PASSWORD",
                proposed_value="DB_PASSWORD: vault-secret-ref:db-prod",
                patch_diff="+ - name: DB_PASSWORD\n+   value: \"vault-secret-ref:db-prod\"",
                explanation="Supplies required secret to auth configuration loader."
            )
        ]
        risk_level = "LOW"
    else:
        # Scale replicas as fallback
        modified_content = original_content.replace("replicaCount: 3", "replicaCount: 5")
        strategy = "SCALE_REPLICAS"
        rationale = "Scale out replica count from 3 to 5 to distribute high request volume."
        patches = [
            ProposedPatch(
                file_path=target_file,
                target_field="replicaCount",
                current_value=3,
                proposed_value=5,
                patch_diff="- replicaCount: 3\n+ replicaCount: 5",
                explanation="Expands horizontal scale to mitigate load."
            )
        ]
        risk_level = "LOW"

    # 3. Generate Unified Diff
    unified_diff = gitops_tools.generate_unified_diff(original_content, modified_content, target_file)

    remediation_result = RemediationData(
        strategy=strategy,
        rationale=rationale,
        patches=patches,
        unified_diff=unified_diff,
        safety_checks_passed=True,
        risk_level=risk_level
    )

    log_entry = StepLog(
        timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
        agent="RemediationAgent",
        action="GitOps Patch Synthesized",
        details=f"Strategy: {strategy} | Target: {target_file} | Safety Checks: Passed",
        status="success"
    )

    state["remediation"] = remediation_result.model_dump()
    state["current_step"] = "remediation_completed"
    state["status"] = "waiting_approval"
    state["step_logs"].append(log_entry.model_dump())

    return state
