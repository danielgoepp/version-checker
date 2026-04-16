import re
import subprocess
from pathlib import Path
import requests
import config
from .utils import print_error

AWX_BASE_URL = "https://awx-prod.goepp.net"
AWX_UPGRADE_TEMPLATE_ID = 32

# Upgrade methods that trigger an AWX job
AWX_UPGRADE_METHODS = {"ansible-helm", "ansible-manifest"}

# Upgrade methods that support manifest-based pinned version updates
MANIFEST_UPGRADE_METHODS = {"ansible-manifest"}


def trigger_awx_upgrade(app_name: str, instance: str, target_instance: str = "", dry_run: bool = False) -> bool:
    """Trigger an AWX job template to upgrade an application.

    Args:
        app_name: Application name (matches k3s_applications key).
        instance: Version-checker instance label (used for error messages).
        target_instance: AWX instance name for multi-instance deployments.
                         Passed as extra var so the playbook can filter to one instance.
        dry_run: If True, print what would happen without calling AWX.

    Returns True if the job was launched (or would be in dry-run), False on failure.
    """
    api_token = config.AWX_API_TOKENS.get("prod")
    if not api_token:
        print_error(instance, "No AWX API token configured for 'prod' instance")
        return False

    url = f"{AWX_BASE_URL}/api/v2/job_templates/{AWX_UPGRADE_TEMPLATE_ID}/launch/"
    extra_vars: dict = {"app_name": app_name}
    if target_instance:
        extra_vars["target_instance"] = target_instance
    payload = {"extra_vars": extra_vars}
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
    """Update a pinned version tag in a Kubernetes manifest file.

    Searches for the current version string (and the 'v'-prefixed form) and
    replaces it with the latest version.  Any suffix after the version (e.g.
    '-ubuntu') and any 'v' prefix are preserved automatically.

    Args:
        manifest_rel_path: Path relative to K3S_CONFIG_FOLDER (e.g. 'grafana/manifests/grafana-prod.yaml').
        current_version: Version currently in the manifest (e.g. '12.1.1').
        latest_version:  Version to upgrade to (e.g. '13.0.0').
        dry_run: If True, print what would change without writing.

    Returns:
        True if the version was found and updated (or would be in dry-run), False otherwise.
    """
    manifest_path = Path(config.K3S_CONFIG_FOLDER) / manifest_rel_path

    if not manifest_path.exists():
        print(f"  Manifest not found: {manifest_path}")
        return False

    if not current_version or not latest_version:
        print(f"  Cannot update manifest: current or latest version is unknown")
        return False

    content = manifest_path.read_text(encoding="utf-8")

    # Try v-prefixed form first, then plain version
    if f"v{current_version}" in content:
        find_str = f"v{current_version}"
        replace_str = f"v{latest_version}"
    elif current_version in content:
        find_str = current_version
        replace_str = latest_version
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


def git_commit_push_manifest(manifest_rel_path: str, app_name: str, latest_version: str, dry_run: bool = False) -> bool:
    """Git add, commit, and push a single manifest file change in the k3s-config repo.

    Returns True on success (including when nothing needed committing), False on failure.
    """
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

    # Stage the file
    result = run_git(["git", "-C", str(repo_path), "add", manifest_full], "git add")
    if result is None:
        return False
    if result.returncode != 0:
        print(f"  git add failed: {(result.stderr or result.stdout).strip()}")
        return False

    # Check if there's anything staged; if not, manifest already matches HEAD
    check = run_git(["git", "-C", str(repo_path), "diff", "--cached", "--quiet"], "git diff --cached")
    if check is not None and check.returncode == 0:
        print(f"  Manifest already at {latest_version} in git — no commit needed")
        return True

    # Commit
    result = run_git(["git", "-C", str(repo_path), "commit", "-m", commit_msg], "git commit")
    if result is None:
        return False
    if result.returncode != 0:
        print(f"  git commit failed: {(result.stderr or result.stdout).strip()}")
        return False

    # Push
    result = run_git(["git", "-C", str(repo_path), "push"], "git push")
    if result is None:
        return False
    if result.returncode != 0:
        print(f"  git push failed: {(result.stderr or result.stdout).strip()}")
        return False

    print(f"  Committed and pushed: {commit_msg}")
    return True
