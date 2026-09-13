# Run KubeOps-Aegis Agent Server locally
Write-Host "⚡ Starting KubeOps-Aegis Autonomous SRE Agent..." -ForegroundColor Cyan

$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn agent.app.main:app --host 0.0.0.0 --port 8000 --reload
