import logging
from datetime import datetime, timezone
from agent.app.core.state import IncidentState, StepLog, TriageData
from agent.app.core.llm import get_llm

logger = logging.getLogger("kubeops.agents.triage")

def triage_agent_node(state: IncidentState) -> IncidentState:
    """Triage Agent: Evaluates alert severity, validates scope, and checks component impact."""
    alert_name = state.get("alert_name", "UnknownAlert")
    resource_name = state.get("resource_name", "unknown-pod")
    namespace = state.get("namespace", "default")
    
    logger.info(f"[TriageAgent] Processing incident {state['incident_id']} - Alert: {alert_name}")
    
    # Categorization logic
    category = "ApplicationError"
    severity = "HIGH"
    assessment = f"Alert '{alert_name}' detected on resource '{resource_name}' in namespace '{namespace}'."
    
    if "oom" in alert_name.lower() or "memory" in alert_name.lower():
        category = "ResourceExhaustion"
        severity = "CRITICAL"
        assessment = f"Container in pod '{resource_name}' is violating memory cgroups limit and experiencing SIGKILL terminations."
    elif "crash" in alert_name.lower() or "backoff" in alert_name.lower():
        category = "CrashLoop"
        severity = "HIGH"
        assessment = f"Pod '{resource_name}' is trapped in CrashLoopBackOff due to initialization or runtime failure."
    elif "cpu" in alert_name.lower() or "throttl" in alert_name.lower():
        category = "PerformanceDegradation"
        severity = "MEDIUM"
        assessment = f"Pod '{resource_name}' is experiencing high CPU throttling, impacting request latency."

    triage_result = TriageData(
        severity=severity,
        category=category,
        affected_components=[resource_name, f"{resource_name}-service"],
        initial_assessment=assessment,
        actionable=True
    )

    log_entry = StepLog(
        timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S"),
        agent="TriageAgent",
        action="Incident Triaged",
        details=f"Severity: {severity} | Category: {category} | Status: Actionable",
        status="warning" if severity in ["HIGH", "CRITICAL"] else "info"
    )

    state["triage"] = triage_result.model_dump()
    state["current_step"] = "triage_completed"
    state["status"] = "diagnosing"
    if "step_logs" not in state or state["step_logs"] is None:
        state["step_logs"] = []
    state["step_logs"].append(log_entry.model_dump())
    
    return state
