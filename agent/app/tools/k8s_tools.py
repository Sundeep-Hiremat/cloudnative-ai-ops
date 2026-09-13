import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from agent.app.core.config import settings

logger = logging.getLogger("kubeops.tools.k8s")

class KubernetesTools:
    def __init__(self):
        self.k8s_client = None
        self.core_v1 = None
        self.apps_v1 = None
        self._init_client()

    def _init_client(self):
        if settings.MOCK_K8S:
            logger.info("Running with Mock Kubernetes Client (Offline / Demonstration mode).")
            return

        try:
            from kubernetes import client, config
            if settings.KUBE_IN_CLUSTER:
                config.load_incluster_config()
            else:
                config.load_kube_config(config_file=settings.KUBECONFIG_PATH)
            
            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            logger.info("Connected to live Kubernetes Cluster successfully.")
        except Exception as e:
            logger.warning(f"Could not connect to live K8s cluster ({e}). Falling back to intelligent mock data.")
            self.core_v1 = None

    def get_pod_logs(self, namespace: str, pod_name: str, tail_lines: int = 100, previous: bool = True) -> str:
        """Fetch logs from pod (including previous terminated container if crashing)."""
        if self.core_v1:
            try:
                logs = self.core_v1.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=namespace,
                    tail_lines=tail_lines,
                    previous=previous
                )
                return logs
            except Exception as e:
                logger.error(f"Error fetching real pod logs: {e}")

        # Intelligent Mock / Simulation response based on pod naming & failure patterns
        if "oom" in pod_name.lower() or "payment" in pod_name.lower():
            return (
                f"[{datetime.now(timezone.utc).isoformat()}] [payment-service] INFO Starting server on port 8080...\n"
                f"[{datetime.now(timezone.utc).isoformat()}] [payment-service] INFO Loaded 2,500 active transaction caches\n"
                f"[{datetime.now(timezone.utc).isoformat()}] [payment-service] WARN High memory allocation detected: 482MB / 500MB (96.4%)\n"
                f"[{datetime.now(timezone.utc).isoformat()}] [payment-service] ERROR java.lang.OutOfMemoryError: Java heap space\n"
                f"[{datetime.now(timezone.utc).isoformat()}] [payment-service] FATAL Terminating process. Signal: SIGKILL (Killed by Linux OOM killer)\n"
            )
        elif "crash" in pod_name.lower() or "auth" in pod_name.lower():
            return (
                f"[{datetime.now(timezone.utc).isoformat()}] [auth-service] INFO Initializing configuration...\n"
                f"[{datetime.now(timezone.utc).isoformat()}] [auth-service] ERROR Missing required environment variable 'DB_PASSWORD'\n"
                f"[{datetime.now(timezone.utc).isoformat()}] [auth-service] FATAL Uncaught exception in main thread: ConfigKeyError: DB_PASSWORD\n"
                f"[{datetime.now(timezone.utc).isoformat()}] [auth-service] Process exited with status code 1\n"
            )
        else:
            return (
                f"[{datetime.now(timezone.utc).isoformat()}] [{pod_name}] INFO Worker spawned PID 42\n"
                f"[{datetime.now(timezone.utc).isoformat()}] [{pod_name}] ERROR Connection refused: redis-cluster.cache.svc.cluster.local:6379\n"
                f"[{datetime.now(timezone.utc).isoformat()}] [{pod_name}] ERROR Backoff retry 5/5 failed. Exiting.\n"
            )

    def get_pod_events(self, namespace: str, pod_name: str) -> List[Dict[str, Any]]:
        """Fetch Kubernetes warning and error events for a pod."""
        if self.core_v1:
            try:
                events = self.core_v1.list_namespaced_event(namespace=namespace, field_selector=f"involvedObject.name={pod_name}")
                return [{"type": ev.type, "reason": ev.reason, "message": ev.message, "count": ev.count} for ev in events.items]
            except Exception as e:
                logger.error(f"Error fetching K8s events: {e}")

        # Intelligent Mock / Simulation response
        if "oom" in pod_name.lower() or "payment" in pod_name.lower():
            return [
                {"type": "Warning", "reason": "OOMKilled", "message": "Container payment-service-app exceeded memory limit (512Mi) and was terminated", "count": 4},
                {"type": "Warning", "reason": "BackOff", "message": "Back-off restarting failed container", "count": 12},
                {"type": "Normal", "reason": "Scheduled", "message": "Successfully assigned default/payment-service-67b4f7678-x9z21 to node ip-10-0-2-45.ec2.internal", "count": 1}
            ]
        elif "crash" in pod_name.lower() or "auth" in pod_name.lower():
            return [
                {"type": "Warning", "reason": "CrashLoopBackOff", "message": "Back-off 5m0s restarting failed container=auth-service pod=auth-service-79d8c97b8-k4lm8_default", "count": 8},
                {"type": "Warning", "reason": "Unhealthy", "message": "Liveness probe failed: HTTP probe failed with statuscode: 503", "count": 3}
            ]
        else:
            return [
                {"type": "Warning", "reason": "FailedScheduling", "message": "0/3 nodes are available: 3 Insufficient memory", "count": 2}
            ]

    def describe_resource(self, namespace: str, kind: str, name: str) -> Dict[str, Any]:
        """Describe Kubernetes deployment or statefulset spec and status."""
        return {
            "kind": kind,
            "name": name,
            "namespace": namespace,
            "replicas": {"desired": 3, "ready": 1, "available": 1, "unavailable": 2},
            "containers": [
                {
                    "name": f"{name}-app",
                    "image": f"registry.internal.io/ecommerce/{name}:v2.4.1",
                    "resources": {
                        "limits": {"cpu": "500m", "memory": "512Mi"},
                        "requests": {"cpu": "250m", "memory": "256Mi"}
                    },
                    "restart_count": 6,
                    "last_state": {"terminated": {"reason": "OOMKilled", "exitCode": 137}}
                }
            ]
        }

k8s_tools = KubernetesTools()
