import logging
import requests
from typing import Dict, Any, Optional
from agent.app.core.config import settings

logger = logging.getLogger("kubeops.tools.prometheus")

class PrometheusTools:
    def __init__(self):
        self.base_url = settings.PROMETHEUS_URL

    def query_promql(self, query: str) -> Dict[str, Any]:
        """Execute a PromQL query against Prometheus or return synthetic metrics."""
        try:
            resp = requests.get(
                f"{self.base_url}/api/v1/query",
                params={"query": query},
                timeout=3
            )
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.debug(f"Prometheus direct query failed ({e}), using synthetic metrics.")

        # Synthetic metric response
        if "container_memory_usage_bytes" in query or "memory" in query.lower():
            return {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {
                            "metric": {"pod": "payment-service-67b4f7678-x9z21", "container": "payment-service-app"},
                            "value": [1718000000, "532676608"]  # ~508 MiB (surpassing 512Mi limit)
                        }
                    ]
                }
            }
        elif "container_cpu_usage_seconds_total" in query or "cpu" in query.lower():
            return {
                "status": "success",
                "data": {
                    "resultType": "vector",
                    "result": [
                        {
                            "metric": {"pod": "payment-service-67b4f7678-x9z21", "container": "payment-service-app"},
                            "value": [1718000000, "0.485"]  # 485m CPU
                        }
                    ]
                }
            }
        else:
            return {
                "status": "success",
                "data": {"resultType": "vector", "result": []}
            }

prometheus_tools = PrometheusTools()
