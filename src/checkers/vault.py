import subprocess
import time
from .kubectl import ImageVersionChecker
from .utils import print_error


def get_vault_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "vault", context=context)
    return checker.get_version_from_image("statefulset", "vault", "hashicorp/vault")


def get_vault_k8s_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "vault", context=context)
    return checker.get_version_from_image("deployment", "vault-agent-injector", "hashicorp/vault-k8s")


def restart_vault_pod(instance, context=None, namespace=None, dry_run=False):
    ns = namespace or "vault"
    ctx = context or "k3s-prod"

    if dry_run:
        print(f"  [DRY RUN] Would delete pod vault-0 in {ns} and wait for restart")
        return True

    cmd = ["kubectl", "--context", ctx, "-n", ns, "delete", "pod", "vault-0"]
    print(f"  {instance}: Deleting vault-0...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print_error(instance, f"Failed to delete vault-0: {result.stderr.strip()}")
        return False

    print(f"  {instance}: Waiting for vault-0 to restart...", flush=True)
    start = time.time()
    while time.time() - start < 120:
        time.sleep(5)
        cmd = ["kubectl", "--context", ctx, "-n", ns, "get", "pod", "vault-0",
               "-o", "jsonpath={.status.phase}"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip() == "Running":
            print(f"  {instance}: vault-0 is running")
            return True

    print_error(instance, "vault-0 did not restart within 120s")
    return False
