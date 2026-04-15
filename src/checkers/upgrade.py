import requests
import config
from .utils import print_error

AWX_BASE_URL = "https://awx-prod.goepp.net"
AWX_UPGRADE_TEMPLATE_ID = 32

# Upgrade methods that trigger an AWX job
AWX_UPGRADE_METHODS = {"ansible-helm", "ansible-manifest"}


def trigger_awx_upgrade(app_name: str, instance: str, dry_run: bool = False) -> bool:
    """Trigger an AWX job template to upgrade an application.

    Returns True if the job was launched (or would be in dry-run), False on failure.
    """
    api_token = config.AWX_API_TOKENS.get("prod")
    if not api_token:
        print_error(instance, "No AWX API token configured for 'prod' instance")
        return False

    url = f"{AWX_BASE_URL}/api/v2/job_templates/{AWX_UPGRADE_TEMPLATE_ID}/launch/"
    payload = {"extra_vars": {"app_name": app_name}}
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
