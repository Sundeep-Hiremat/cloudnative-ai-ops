#!/usr/bin/env python3
"""
Interactive CLI incident simulator for interview demos.
Sends chaos alerts to KubeOps-Aegis and displays real-time step streaming.
"""
import sys
import time
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()

BASE_URL = "http://localhost:8000"

def main():
    console.print(Panel.fit(
        "[bold cyan]⚡ KubeOps-Aegis Autonomous SRE Incident Simulator[/bold cyan]\n"
        "[dim]Demonstrate real-time AI-Ops triage, diagnosis, GitOps PR generation & self-healing[/dim]",
        border_style="cyan"
    ))

    scenarios = {
        "1": ("oom", "KubeContainerOOMKilled - Memory starvation under peak load"),
        "2": ("crashloop", "KubePodCrashLoopBackOff - Missing configuration/secret"),
        "3": ("throttling", "KubeCPUThrottlingHigh - Extreme CPU starvation")
    }

    console.print("\n[bold yellow]Select a Chaos Scenario to inject:[/bold yellow]")
    for key, (sc, desc) in scenarios.items():
        console.print(f"  [bold green]{key}[/bold green]: {desc}")

    choice = input("\nEnter choice [1-3] (default: 1): ").strip() or "1"
    scenario, description = scenarios.get(choice, scenarios["1"])

    console.print(f"\n[bold red]💥 Injecting scenario: {scenario}...[/bold red]")
    try:
        resp = requests.post(
            f"{BASE_URL}/api/chaos/trigger",
            json={"scenario": scenario, "service": "payment-service", "namespace": "default"},
            timeout=5
        )
        if resp.status_code != 200:
            console.print(f"[bold red]Failed to trigger incident: {resp.text}[/bold red]")
            return
        
        data = resp.json()
        incident_id = data["incident_id"]
        console.print(f"[bold green]✅ Incident Ingested! Incident ID:[/bold green] [bold cyan]{incident_id}[/bold cyan]")
        
        console.print("\n[bold cyan]⏳ Monitoring LangGraph Autonomous Agents...[/bold cyan]\n")
        
        # Poll and display state progression
        last_step_count = 0
        while True:
            time.sleep(1.0)
            res = requests.get(f"{BASE_URL}/api/incidents/{incident_id}")
            if res.status_code != 200:
                continue
            
            inc = res.json()
            step_logs = inc.get("step_logs", [])
            
            # Print new logs
            for log in step_logs[last_step_count:]:
                agent = log["agent"]
                action = log["action"]
                details = log["details"]
                status = log["status"]
                
                color = "green" if status == "success" else "yellow" if status == "warning" else "cyan"
                console.print(f"  [{color}]• [{log['timestamp']}][/{color}] [bold {color}][{agent}][/bold {color}] [bold]{action}[/bold]: {details}")
                
            last_step_count = len(step_logs)
            
            if inc.get("status") == "waiting_approval":
                console.print(f"\n[bold yellow]⏸️  LangGraph State Machine Paused at Human-in-the-Loop Checkpoint[/bold yellow]")
                
                remediation = inc.get("remediation", {})
                unified_diff = remediation.get("unified_diff", "")
                
                if unified_diff:
                    console.print("\n[bold]Proposed GitOps Diff:[/bold]")
                    syntax = Syntax(unified_diff, "diff", theme="monokai", line_numbers=False)
                    console.print(syntax)
                
                approve = input("\n👉 Approve and merge GitOps PR to ArgoCD? (Y/n): ").strip().lower()
                if approve in ["", "y", "yes"]:
                    console.print("\n[bold green]🚀 Merging PR & Triggering ArgoCD sync...[/bold green]")
                    requests.post(f"{BASE_URL}/api/incidents/{incident_id}/approve", json={"comment": "Approved via CLI"})
                else:
                    console.print("\n[bold red]❌ Rejecting proposed fix...[/bold red]")
                    requests.post(f"{BASE_URL}/api/incidents/{incident_id}/reject", json={"comment": "Rejected via CLI"})
                    break
                    
            elif inc.get("status") == "resolved":
                console.print("\n" + "="*70)
                console.print("[bold green]🎉 Incident Resolved & Verified by ArgoCD![/bold green]")
                console.print(f"[dim]View full dashboard at: {BASE_URL}[/dim]")
                console.print("="*70 + "\n")
                break

    except requests.exceptions.ConnectionError:
        console.print(f"[bold red]❌ Could not connect to {BASE_URL}. Ensure the agent is running via scripts/run_agent.ps1[/bold red]")

if __name__ == "__main__":
    main()
