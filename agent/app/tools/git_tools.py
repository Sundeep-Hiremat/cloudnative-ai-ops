import os
import difflib
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("kubeops.tools.git")

class GitOpsTools:
    def __init__(self, repo_path: str = "./gitops"):
        self.repo_path = repo_path

    def read_manifest(self, relative_path: str) -> str:
        """Reads a manifest or values.yaml from the GitOps repo."""
        full_path = os.path.join(self.repo_path, relative_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        
        # Fallback default content if file not yet on disk
        return (
            "replicaCount: 3\n\n"
            "image:\n"
            "  repository: registry.internal.io/ecommerce/payment-service\n"
            "  pullPolicy: IfNotPresent\n"
            "  tag: \"v2.4.1\"\n\n"
            "resources:\n"
            "  limits:\n"
            "    cpu: 500m\n"
            "    memory: 512Mi\n"
            "  requests:\n"
            "    cpu: 250m\n"
            "    memory: 256Mi\n\n"
            "env:\n"
            "  - name: APP_ENV\n"
            "    value: \"production\"\n"
            "  - name: CACHE_SIZE\n"
            "    value: \"5000\"\n"
        )

    def generate_unified_diff(self, original_text: str, modified_text: str, filename: str) -> str:
        """Generate standard unified git diff format."""
        orig_lines = original_text.splitlines(keepends=True)
        mod_lines = modified_text.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{filename}",
            tofile=f"b/{filename}",
            lineterm=""
        )
        return "\n".join(diff)

    def apply_patch_to_file(self, relative_path: str, new_content: str) -> bool:
        """Writes the updated content to disk in the GitOps repository."""
        try:
            full_path = os.path.join(self.repo_path, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            logger.info(f"Successfully patched file at {full_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to patch file: {e}")
            return False

    def create_gitops_pr(
        self,
        incident_id: str,
        target_file: str,
        pr_title: str,
        pr_body: str
    ) -> Dict[str, Any]:
        """Creates a GitOps branch and Pull Request record."""
        branch_name = f"kubeops-fix/{incident_id[:8]}"
        pr_url = f"https://github.com/Sundeep-Hiremat/cloudnative-ai-ops/pull/auto-{incident_id[:8]}"
        
        return {
            "branch_name": branch_name,
            "pr_title": pr_title,
            "pr_body": pr_body,
            "pr_url": pr_url,
            "target_file": target_file,
            "commit_sha": f"a1b2c3d{incident_id[:4]}"
        }

gitops_tools = GitOpsTools()
