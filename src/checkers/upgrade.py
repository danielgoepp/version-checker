import json
import re
import subprocess
import time
from pathlib import Path
import requests
import config
from .utils import print_error

AWX_OPS_UPGRADE_ESPHOME_TEMPLATE_ID = 31
AWX_OPS_UPGRADE_K3S_TEMPLATE_ID = 32
AWX_OPS_UPGRADE_SERVER_TEMPLATE_ID = 47
AWX_OPS_UPGRADE_LLM_TEMPLATE_ID = 48
AWX_OPS_VAULT_UPGRADE_WORKFLOW_ID = 50
AWX_OPS_UPGRADE_UOS_TEMPLATE_ID = 42

AWX_UPGRADE_METHODS = {"ansible-helm", "ansible-manifest", "ansible-apt", "ansible-llm", "ansible-esphome", "ansible-calico", "ansible-uos"}
MANIFEST_UPGRADE_METHODS = {"ansible-manifest"}
HELM_UPGRADE_METHODS = {"ansible-helm"}
CR_UPGRADE_METHODS = {"ansible-cr"}

_TERMINAL_STATUSES = {"successful", "failed", "error", "canceled"}
_POLL_INTERVAL = 5
_POLL_TIMEOUT = 600


def wait_for_awx_job(job_id: int, instance: str, api_token: str, resource: str = "jobs") -> bool:
    headers = {"Authorization": f"Bearer {api_token}"}
    job_url = f"{config.AWX_BASE_URL}/api/v2/{resource}/{job_id}/"

    print(f"  Waiting for job {job_id}...", end="", flush=True)
    elapsed = 0
    while elapsed < _POLL_TIMEOUT:
        time.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL
        try:
            resp = requests.get(job_url, headers=headers, timeout=15, verify=True)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print()
            print_error(instance, f"Error polling job {job_id}: {e}")
            continue

        status = data.get("status", "unknown")
        if status not in _TERMINAL_STATUSES:
            print(".", end="", flush=True)
            continue

        job_elapsed = data.get("elapsed")
        elapsed_str = f"{job_elapsed:.1f}s" if job_elapsed is not None else f"{elapsed}s"
        if status == "successful":
            print(f" succeeded ({elapsed_str})")
        else:
            print(f" {status} ({elapsed_str})")

        return status == "successful"

    print()
    print_error(instance, f"Job {job_id} timed out after {_POLL_TIMEOUT}s")
    return False


def _launch_awx_job(instance: str, template_id: int, extra_vars: dict | None = None,
                    dry_run: bool = False, wait: bool = True, workflow: bool = False) -> bool:
    api_token = config.AWX_API_TOKENS.get("prod")
    if not api_token:
        print_error(instance, "No AWX API token configured for 'prod' instance")
        return False

    resource = "workflow_job_templates" if workflow else "job_templates"
    url = f"{config.AWX_BASE_URL}/api/v2/{resource}/{template_id}/launch/"
    payload = {"extra_vars": json.dumps(extra_vars)} if extra_vars else None
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    if dry_run:
        print(f"  [DRY RUN] Would POST to {url}")
        if payload:
            print(f"  [DRY RUN] Payload: {payload}")
        return True

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15, verify=True)
        response.raise_for_status()
        data = response.json()
        job_id = data.get("workflow_job") or data.get("job") or data.get("id")
        if not job_id:
            print("  AWX job launched (no job ID in response)")
            return True
        link_kind = "workflow" if workflow else "playbook"
        print(f"  AWX job launched: {config.AWX_BASE_URL}/#/jobs/{link_kind}/{job_id}/details")
        if not wait:
            return True
        return wait_for_awx_job(job_id, instance, api_token, resource="workflow_jobs" if workflow else "jobs")
    except requests.HTTPError as e:
        print_error(instance, f"AWX API error ({e.response.status_code}): {e.response.text[:200]}")
        return False
    except requests.RequestException as e:
        print_error(instance, f"AWX request failed: {e}")
        return False


def trigger_awx_upgrade(app_name: str, instance: str, dry_run: bool = False) -> bool:
    return _launch_awx_job(instance, AWX_OPS_UPGRADE_K3S_TEMPLATE_ID, {"app_name": app_name}, dry_run=dry_run)


def trigger_awx_apt_upgrade(target_host: str, instance: str, dry_run: bool = False) -> bool:
    return _launch_awx_job(instance, AWX_OPS_UPGRADE_SERVER_TEMPLATE_ID, {"target_host": target_host}, dry_run=dry_run)


def trigger_awx_llm_upgrade(component: str, instance: str, dry_run: bool = False) -> bool:
    return _launch_awx_job(instance, AWX_OPS_UPGRADE_LLM_TEMPLATE_ID, {"llm_upgrade_component": component}, dry_run=dry_run)


def trigger_awx_calico_upgrade(target_version: str, instance: str, dry_run: bool = False) -> bool:
    return _launch_awx_job(
        instance, AWX_OPS_UPGRADE_K3S_TEMPLATE_ID,
        {"app_name": "calico", "calico_target_version": target_version}, dry_run=dry_run,
    )


def trigger_awx_esphome_upgrade(target_pattern: str, instance: str, dry_run: bool = False) -> bool:
    # No wait: ESPHome compiles take too long to poll for.
    return _launch_awx_job(
        instance, AWX_OPS_UPGRADE_ESPHOME_TEMPLATE_ID,
        {"target_pattern": target_pattern, "esphome_clean_build": "true"}, dry_run=dry_run, wait=False,
    )


def trigger_awx_uos_upgrade(instance: str, dry_run: bool = False) -> bool:
    # Self-contained playbook/inventory — no extra_vars; no wait.
    return _launch_awx_job(instance, AWX_OPS_UPGRADE_UOS_TEMPLATE_ID, dry_run=dry_run, wait=False)


def trigger_vault_upgrade_workflow(instance: str, dry_run: bool = False) -> bool:
    return _launch_awx_job(instance, AWX_OPS_VAULT_UPGRADE_WORKFLOW_ID, dry_run=dry_run, workflow=True)


def _update_version_in_file(
    rel_path: str, current_version: str, latest_version: str, label: str, dry_run: bool = False
) -> bool:
    path = Path(config.K3S_CONFIG_FOLDER) / rel_path

    if not path.exists():
        print(f"  {label} not found: {path}")
        return False

    if not current_version or not latest_version:
        print(f"  Cannot update {label.lower()}: current or latest version is unknown")
        return False

    content = path.read_text(encoding="utf-8")

    # Anchored so the version can't match inside a longer token (another
    # version, an IP, a digest); suffixed tags like :1.2.3-ubuntu still match
    # and the optional v prefix is preserved per occurrence.
    def _anchored(version):
        return re.compile(rf"(?<![\w.])(v?){re.escape(version)}(?![\w.])")

    current_re = _anchored(current_version)
    if not current_re.search(content):
        if _anchored(latest_version).search(content):
            print(f"  {label} already at {latest_version} — no update needed")
        else:
            print(f"  Version '{current_version}' not found in {rel_path}")
        return False

    updated, count = current_re.subn(lambda m: m.group(1) + latest_version, content)

    if dry_run:
        print(f"  [DRY RUN] Would update {rel_path}: {current_version} → {latest_version} ({count} occurrence(s))")
        return True

    path.write_text(updated, encoding="utf-8")
    print(f"  Updated {rel_path}: {current_version} → {latest_version} ({count} occurrence(s))")
    return True


def update_manifest_version(
    manifest_rel_path: str, current_version: str, latest_version: str, dry_run: bool = False
) -> bool:
    return _update_version_in_file(manifest_rel_path, current_version, latest_version, "Manifest", dry_run=dry_run)


def update_helm_values_version(
    values_rel_path: str, current_version: str, latest_version: str, dry_run: bool = False
) -> bool:
    return _update_version_in_file(values_rel_path, current_version, latest_version, "Helm values", dry_run=dry_run)


def git_commit_push_manifest(manifest_rel_path: str, app_name: str, latest_version: str, dry_run: bool = False, extra_rel_paths: list[str] | None = None) -> bool:
    repo_path = Path(config.K3S_CONFIG_FOLDER)
    all_rel_paths = [manifest_rel_path] + (extra_rel_paths or [])
    all_full_paths = [str(repo_path / p) for p in all_rel_paths]
    commit_msg = f"Update {app_name} to {latest_version}"

    if dry_run:
        for cmd, label in [
            (["git", "-C", str(repo_path), "add"] + all_full_paths, "git add"),
            (["git", "-C", str(repo_path), "commit", "-m", commit_msg], "git commit"),
            (["git", "-C", str(repo_path), "push"], "git push"),
        ]:
            print(f"  [DRY RUN] Would run: {' '.join(cmd)}")
        return True

    def run_git(cmd: list, label: str) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            print(f"  {label} timed out")
            return None
        except FileNotFoundError:
            print(f"  git not found in PATH")
            return None

    result = run_git(["git", "-C", str(repo_path), "add"] + all_full_paths, "git add")
    if result is None:
        return False
    if result.returncode != 0:
        print(f"  git add failed: {(result.stderr or result.stdout).strip()}")
        return False

    check = run_git(["git", "-C", str(repo_path), "diff", "--cached", "--quiet"], "git diff --cached")
    if check is not None and check.returncode == 0:
        print(f"  Manifest already at {latest_version} in git — no commit needed")
        return True

    result = run_git(["git", "-C", str(repo_path), "commit", "-m", commit_msg], "git commit")
    if result is None:
        return False
    if result.returncode != 0:
        print(f"  git commit failed: {(result.stderr or result.stdout).strip()}")
        return False

    result = run_git(["git", "-C", str(repo_path), "push"], "git push")
    if result is None:
        return False
    if result.returncode != 0:
        print(f"  git push failed: {(result.stderr or result.stdout).strip()}")
        return False

    print(f"  Committed and pushed: {commit_msg}")
    return True


def kubectl_apply_manifest(manifest_rel_path: str, context: str, namespace: str, instance: str, dry_run: bool = False) -> bool:
    manifest_path = Path(config.K3S_CONFIG_FOLDER) / manifest_rel_path

    if not manifest_path.exists():
        print(f"  Manifest not found: {manifest_path}")
        return False

    cmd = ["kubectl", "apply", "-f", str(manifest_path)]
    if context:
        cmd.extend(["--context", context])
    if namespace:
        cmd.extend(["--namespace", namespace])

    if dry_run:
        print(f"  [DRY RUN] Would run: {' '.join(cmd)}")
        return True

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"  kubectl apply succeeded: {result.stdout.strip()}")
            return True
        else:
            print(f"  kubectl apply failed: {(result.stderr or result.stdout).strip()}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  kubectl apply timed out")
        return False
    except FileNotFoundError:
        print(f"  kubectl not found in PATH")
        return False
