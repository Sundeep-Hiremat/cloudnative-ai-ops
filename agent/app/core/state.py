from typing import List, Dict, Any, Optional, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class StepLog(BaseModel):
    timestamp: str
    agent: str
    action: str
    details: str
    status: Literal["info", "success", "warning", "error"] = "info"

class TriageData(BaseModel):
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = "HIGH"
    category: str  # e.g., "ResourceExhaustion", "ApplicationCrash", "ConfigurationError", "Network"
    affected_components: List[str] = Field(default_factory=list)
    initial_assessment: str = ""
    actionable: bool = True

class DiagnosticData(BaseModel):
    root_cause: str = ""
    evidence_logs: List[str] = Field(default_factory=list)
    evidence_events: List[str] = Field(default_factory=list)
    evidence_metrics: Dict[str, Any] = Field(default_factory=dict)
    confidence_score: float = 0.0  # 0.0 to 1.0
    impact_analysis: str = ""

class ProposedPatch(BaseModel):
    file_path: str
    target_field: str
    current_value: Any
    proposed_value: Any
    patch_diff: str
    explanation: str

class RemediationData(BaseModel):
    strategy: Literal["PATCH_GITOPS_VALUES", "ROLLBACK_IMAGE", "SCALE_REPLICAS", "RESOURCE_BUMP", "CONFIG_FIX"]
    rationale: str
    patches: List[ProposedPatch] = Field(default_factory=list)
    unified_diff: str = ""
    safety_checks_passed: bool = True
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"

class GitOpsPRData(BaseModel):
    branch_name: str = ""
    pr_title: str = ""
    pr_body: str = ""
    pr_url: Optional[str] = None
    commit_sha: Optional[str] = None
    target_file: str = ""

class VerificationData(BaseModel):
    status: Literal["PENDING", "VERIFIED_HEALTHY", "DEGRADED", "FAILED"] = "PENDING"
    checks_performed: List[str] = Field(default_factory=list)
    metrics_summary: Dict[str, Any] = Field(default_factory=dict)
    cluster_status: str = ""

# LangGraph Incident State
class IncidentState(TypedDict):
    incident_id: str
    alert_name: str
    namespace: str
    resource_kind: str
    resource_name: str
    labels: Dict[str, str]
    annotations: Dict[str, str]
    raw_alert: Dict[str, Any]
    current_step: str
    step_logs: List[Dict[str, Any]]
    
    triage: Optional[Dict[str, Any]]
    diagnostic: Optional[Dict[str, Any]]
    remediation: Optional[Dict[str, Any]]
    gitops_pr: Optional[Dict[str, Any]]
    
    approval_status: Literal["pending", "approved", "rejected", "skipped"]
    approval_comment: Optional[str]
    
    verification: Optional[Dict[str, Any]]
    post_mortem: Optional[str]
    status: Literal["triaging", "diagnosing", "remediating", "waiting_approval", "applying", "verifying", "resolved", "failed", "rejected"]
    error: Optional[str]
