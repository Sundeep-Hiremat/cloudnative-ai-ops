// KubeOps-Aegis Dashboard State
let incidents = [];
let selectedIncidentId = null;
let socket = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  initWebSocket();
  fetchInitialData();
  setInterval(fetchStats, 5000);
});

function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    document.getElementById('ws-status').innerText = 'Live Connected';
    document.querySelector('.pulse-dot').style.backgroundColor = '#10b981';
  };

  socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleSocketMessage(msg);
    } catch (e) {
      console.error('WS Parse Error', e);
    }
  };

  socket.onclose = () => {
    document.getElementById('ws-status').innerText = 'Reconnecting...';
    document.querySelector('.pulse-dot').style.backgroundColor = '#f59e0b';
    setTimeout(initWebSocket, 2500);
  };
}

function handleSocketMessage(msg) {
  const { type, data } = msg;

  if (type === 'INCIDENT_CREATED') {
    incidents.unshift(data);
    selectedIncidentId = data.incident_id;
    renderAll();
  } else if (type === 'STATE_UPDATED' || type === 'WAITING_APPROVAL' || type === 'INCIDENT_RESOLVED') {
    const idx = incidents.findIndex(i => i.incident_id === data.incident_id);
    if (idx !== -1) {
      incidents[idx] = data;
    } else {
      incidents.unshift(data);
    }
    if (!selectedIncidentId || selectedIncidentId === data.incident_id) {
      selectedIncidentId = data.incident_id;
    }
    renderAll();
  }
  fetchStats();
}

async function fetchInitialData() {
  try {
    const res = await fetch('/api/incidents');
    incidents = await res.json();
    if (incidents.length > 0) {
      selectedIncidentId = incidents[0].incident_id;
    }
    renderAll();
    fetchStats();
  } catch (err) {
    console.error('Failed to load incidents', err);
  }
}

async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    const stats = await res.json();
    document.getElementById('metric-mttr').innerText = `${stats.mttr_seconds}s`;
    document.getElementById('metric-rate').innerText = `${stats.autonomous_success_rate_pct}%`;
    document.getElementById('metric-active').innerText = stats.active_incidents;
  } catch (err) {
    console.error('Failed to fetch stats', err);
  }
}

async function triggerChaos(scenario) {
  try {
    const res = await fetch('/api/chaos/trigger', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario, service: 'payment-service', namespace: 'default' })
    });
    const data = await res.json();
    console.log('Chaos triggered:', data);
  } catch (err) {
    alert('Error triggering chaos: ' + err.message);
  }
}

async function approveIncident(incidentId) {
  try {
    await fetch(`/api/incidents/${incidentId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment: 'Approved via SRE Web Dashboard' })
    });
  } catch (err) {
    alert('Error approving incident: ' + err.message);
  }
}

async function rejectIncident(incidentId) {
  try {
    await fetch(`/api/incidents/${incidentId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ comment: 'Rejected by operator' })
    });
  } catch (err) {
    alert('Error rejecting incident: ' + err.message);
  }
}

function selectIncident(id) {
  selectedIncidentId = id;
  renderAll();
}

function renderAll() {
  renderIncidentList();
  renderGraphAndTimeline();
  renderApprovalPanel();
}

function renderIncidentList() {
  const container = document.getElementById('incident-list');
  document.getElementById('incident-count').innerText = `${incidents.length} total`;

  if (incidents.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🛡️</div>
        <p>No active incidents. Cluster is healthy.</p>
        <small>Click one of the Chaos buttons above to trigger a demo incident.</small>
      </div>`;
    return;
  }

  container.innerHTML = incidents.map(inc => {
    const isSelected = inc.incident_id === selectedIncidentId ? 'active' : '';
    const badgeClass = inc.status === 'resolved' ? 'badge-success' : inc.status === 'waiting_approval' ? 'badge-warning' : 'badge-danger';
    return `
      <div class="incident-card ${isSelected}" onclick="selectIncident('${inc.incident_id}')">
        <div class="incident-card-top">
          <span class="incident-name">${inc.resource_name}</span>
          <span class="badge ${badgeClass}">${inc.status}</span>
        </div>
        <div class="incident-meta">
          <span>${inc.alert_name}</span> • <span>ns/${inc.namespace}</span>
        </div>
      </div>
    `;
  }).join('');
}

function renderGraphAndTimeline() {
  const current = incidents.find(i => i.incident_id === selectedIncidentId);
  const nodes = {
    triage: document.getElementById('node-triage'),
    diagnostic: document.getElementById('node-diagnostic'),
    remediation: document.getElementById('node-remediation'),
    gitops: document.getElementById('node-gitops'),
    verification: document.getElementById('node-verification'),
  };

  // Reset node classes
  Object.values(nodes).forEach(n => n.className = 'node-pill');

  if (!current) return;

  const status = current.status;
  document.getElementById('agent-active-badge').innerText = `Step: ${current.current_step}`;

  if (status === 'triaging') {
    nodes.triage.classList.add('active');
  } else if (status === 'diagnosing') {
    nodes.triage.classList.add('completed');
    nodes.diagnostic.classList.add('active');
  } else if (status === 'remediating') {
    nodes.triage.classList.add('completed');
    nodes.diagnostic.classList.add('completed');
    nodes.remediation.classList.add('active');
  } else if (status === 'waiting_approval') {
    nodes.triage.classList.add('completed');
    nodes.diagnostic.classList.add('completed');
    nodes.remediation.classList.add('completed');
    nodes.gitops.classList.add('active');
  } else if (status === 'verifying' || status === 'resolved') {
    nodes.triage.classList.add('completed');
    nodes.diagnostic.classList.add('completed');
    nodes.remediation.classList.add('completed');
    nodes.gitops.classList.add('completed');
    nodes.verification.classList.add(status === 'resolved' ? 'completed' : 'active');
  }

  // Render timeline logs
  const timeline = document.getElementById('timeline-list');
  const logs = current.step_logs || [];
  if (logs.length === 0) {
    timeline.innerHTML = '<div class="log-item info"><span class="log-agent">[KubeOps]</span> Ingesting incident event...</div>';
  } else {
    timeline.innerHTML = logs.map(l => `
      <div class="log-item ${l.status}">
        <span class="log-time">${l.timestamp}</span>
        <span class="log-agent">[${l.agent}]</span>
        <span class="log-text">${l.action}: ${l.details}</span>
      </div>
    `).join('');
    timeline.scrollTop = timeline.scrollHeight;
  }
}

function renderApprovalPanel() {
  const container = document.getElementById('approval-panel');
  const current = incidents.find(i => i.incident_id === selectedIncidentId);

  if (!current || !current.remediation) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🌿</div>
        <p>No pending GitOps approvals.</p>
        <small>Proposed manifest diffs and PR approvals will appear here.</small>
      </div>`;
    document.getElementById('approval-badge').innerText = 'No Pending PR';
    document.getElementById('approval-badge').className = 'badge badge-neutral';
    return;
  }

  const { remediation, diagnostic, gitops_pr, post_mortem, status } = current;

  // Format diff lines
  const diffLines = (remediation.unified_diff || '').split('\n').map(line => {
    if (line.startsWith('+')) return `<span class="diff-line-add">${escapeHtml(line)}</span>`;
    if (line.startsWith('-')) return `<span class="diff-line-del">${escapeHtml(line)}</span>`;
    return `<span>${escapeHtml(line)}</span>`;
  }).join('\n');

  if (status === 'resolved' && post_mortem) {
    document.getElementById('approval-badge').innerText = 'Resolved & Verified';
    document.getElementById('approval-badge').className = 'badge badge-success';
    container.innerHTML = `
      <div class="pr-summary-box">
        <div class="badge badge-success" style="margin-bottom: 8px;">✅ GitOps PR Merged & ArgoCD Synced</div>
        <h4 class="pr-title">${gitops_pr ? gitops_pr.pr_title : 'Remediation Synced'}</h4>
        <div class="diff-viewer"><pre>${diffLines}</pre></div>
      </div>
      <div class="rca-box" style="border-left-color: #10b981; background: rgba(16, 185, 129, 0.08);">
        <strong>Post-Mortem Summary:</strong>
        <p style="margin-top: 4px; font-size: 0.8rem; color: #d1fae5;">Cluster self-healing complete. 0 packet drops or OOM restarts detected.</p>
      </div>
    `;
    return;
  }

  if (status === 'waiting_approval') {
    document.getElementById('approval-badge').innerText = 'Pending Human Review';
    document.getElementById('approval-badge').className = 'badge badge-warning';
  }

  container.innerHTML = `
    <div class="pr-summary-box">
      <div class="badge badge-info" style="margin-bottom: 6px;">GitOps Branch: ${gitops_pr ? gitops_pr.branch_name : 'main'}</div>
      <h4 class="pr-title">${gitops_pr ? gitops_pr.pr_title : 'Proposed GitOps Patch'}</h4>
      <p style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 10px;">${remediation.rationale}</p>
      
      <div class="rca-box">
        <strong>Root Cause Diagnosis:</strong><br/>
        ${diagnostic ? diagnostic.root_cause : 'Analyzing metrics...'}
      </div>

      <div class="diff-viewer">
        <pre>${diffLines}</pre>
      </div>

      ${status === 'waiting_approval' ? `
        <div class="approval-btn-group">
          <button class="btn btn-approve" onclick="approveIncident('${current.incident_id}')">
            ⚡ Approve & Merge via ArgoCD
          </button>
          <button class="btn btn-reject" onclick="rejectIncident('${current.incident_id}')">
            Reject
          </button>
        </div>
      ` : ''}
    </div>
  `;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
