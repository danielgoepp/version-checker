import json
import re
import subprocess
from pathlib import Path
import requests
import config
from .utils import print_error

AWX_BASE_URL = "https://awx-prod.goepp.net"
AWX_OPS_UPGRADE_K3S_TEMPLATE_ID = 32
AWX_OPS_UPGRADE_SERVER_TEMPLATE_ID = 47

AWX_UPGRADE_METHODS = {"ansible-helm", "ansible-manifest", "ansible-apt"}
MANIFEST_UPGRADE_METHODS = {"ansible-manifest"}
HELM_UPGRADE_METHODS = {"ansible-helm"}


def trigger_awx_apt_upgrade(target_host: str, instance: str, dry_run: bool = False) -> bool:
    api_token = config.AWX_API_TOKENS.get("prod")
    if not api_token:
        print_error(instance, "No AWX API token configured for 'prod' instance")
        return False

    url = f"{AWX_BASE_URL}/api/v2/job_templates/{AWX_OPS_UPGRADE_SERVER_TEMPLATE_ID}/launch/"
    payload = {"extra_vars": json.dumps({"target_host": target_host})}
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    if dry_run:
        print(f"  [DRY RUN] Would POST to {url}")
        print(f"  [DRY RUN] Payload: {payload}")
        return True

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15, verify=True)
        response.raise_for_status()
        data = response.json()
        job_id = data.get("job") or data.get("id")
        if job_id:
            print(f"  AWX job launched: {AWX_BASE_URL}/#/jobs/playbook/{job_id}/details")
        else:
            print(f"  AWX job launched (no job ID in response)")
        return True
    except requests.HTTPError as e:
        print_error(instance, f"AWX API error ({e.response.status_code}): {e.response.text[:200]}")
        return False
    except requests.RequestException as e:
        print_error(instance, f"AWX request failed: {e}")
        return False


def trigger_awx_upgrade(app_name: str, instance: str, dry_run: bool = False) -> bool:
    api_token = config.AWX_API_TOKENS.get("prod")
    if not api_token:
        print_error(instance, "No AWX API token configured for 'prod' instance")
        return False

    url = f"{AWX_BASE_URL}/api/v2/job_templates/{AWX_OPS_UPGRADE_K3S_TEMPLATE_ID}/launch/"
    payload = {"extra_vars": json.dumps({"app_name": app_name})}
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    if dry_run:
        print(f"  [DRY RUN] Would POST to {url}")
        print(f"  [DRY RUN] Payload: {payload}")
        return True

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15, verify=True)
        response.raise_for_status()
        data = response.json()
        job_id = data.get("job") or data.get("id")
        if job_id:
            print(f"  AWX job launched: {AWX_BASE_URL}/#/jobs/playbook/{job_id}/details")
        else:
            print(f"  AWX job launched (no job ID in response)")
        return True
    except requests.HTTPError as e:
        print_error(instance, f"AWX API error ({e.response.status_code}): {e.response.text[:200]}")
        return False
    except requests.RequestException as e:
        print_error(instance, f"AWX request failed: {e}")
        return False


def update_manifest_version(
    manifest_rel_path: str, current_version: str, latest_version: str, dry_run: bool = False
) -> bool:
    manifest_path = Path(config.K3S_CONFIG_FOLDER) / manifest_rel_path

    if not manifest_path.exists():
        print(f"  Manifest not found: {manifest_path}")
        return False

    if not current_version or not latest_version:
        print(f"  Cannot update manifest: current or latest version is unknown")
        return False

    content = manifest_path.read_text(encoding="utf-8")

    if f"v{current_version}" in content:
        find_str = f"v{current_version}"
        replace_str = f"v{latest_version}"
    elif current_version in content:
        find_str = current_version
        replace_str = latest_version
    elif latest_version in content or f"v{latest_version}" in content:
        print(f"  Manifest already at {latest_version} — no update needed")
        return False
    else:
        print(f"  Version '{current_version}' not found in {manifest_rel_path}")
        return False

    updated = content.replace(find_str, replace_str)

    if dry_run:
        print(f"  [DRY RUN] Would update {manifest_rel_path}: '{find_str}' → '{replace_str}'")
        return True

    manifest_path.write_text(updated, encoding="utf-8")
    print(f"  Updated {manifest_rel_path}: '{find_str}' → '{replace_str}'")
    return True


def update_helm_values_version(
    values_rel_path: str, current_version: str, latest_version: str, dry_run: bool = False
) -> bool:
    values_path = Path(config.K3S_CONFIG_FOLDER) / values_rel_path

    if not values_path.exists():
        print(f"  Helm values file not found: {values_path}")
        return False

    if not current_version or not latest_version:
        print(f"  Cannot update helm values: current or latest version is unknown")
        return False

    content = values_path.read_text(encoding="utf-8")

    if f"v{current_version}" in content:
        find_str = f"v{current_version}"
        replace_str = f"v{latest_version}"
    elif current_version in content:
        find_str = current_version
        replace_str = latest_version
    elif latest_version in content or f"v{latest_version}" in content:
        print(f"  Helm values already at {latest_version} — no update needed")
        return False
    else:
        print(f"  Version '{current_version}' not found in {values_rel_path}")
        return False

    updated = content.replace(find_str, replace_str)

    if dry_run:
        print(f"  [DRY RUN] Would update {values_rel_path}: '{find_str}' → '{replace_str}'")
        return True

    values_path.write_text(updated, encoding="utf-8")
    print(f"  Updated {values_rel_path}: '{find_str}' → '{replace_str}'")
    return True


def git_commit_push_manifest(manifest_rel_path: str, app_name: str, latest_version: str, dry_run: bool = False) -> bool:
    repo_path = Path(config.K3S_CONFIG_FOLDER)
    manifest_full = str(repo_path / manifest_rel_path)
    commit_msg = f"Update {app_name} to {latest_version}"

    if dry_run:
        for cmd, label in [
            (["git", "-C", str(repo_path), "add", manifest_full], "git add"),
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

    result = run_git(["git", "-C", str(repo_path), "add", manifest_full], "git add")
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
