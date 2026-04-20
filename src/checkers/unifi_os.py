import requests
from .utils import print_error, handle_timeout_error, handle_generic_error
import config


def get_unifi_os_nvr_latest_version(current_version=None):
    try:
        import xml.etree.ElementTree as ET
        import re

        rss_url = "https://community.ui.com/rss/releases/UniFi%20Protect%20NVR/ba34c1fa-d237-4161-872b-c3104ef77085"

        headers = {
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'User-Agent': 'Version Checker 1.0'
        }

        response = requests.get(rss_url, headers=headers, timeout=30, verify=True)

        if response.status_code == 200:
            root = ET.fromstring(response.content)

            items = root.findall('.//item')
            if items:
                first_item = items[0]
                title = first_item.find('title')
                if title is not None:
                    title_text = title.text
                    version_match = re.search(r'UniFi OS - Network Video Recorders\s+([\d.]+)', title_text)
                    if version_match:
                        rss_version = version_match.group(1)

                        # If current is newer than RSS stable, user is on early access
                        if current_version and _is_version_newer(current_version, rss_version):
                            return current_version

                        return rss_version

        return None

    except requests.exceptions.Timeout:
        print("Timeout getting latest UniFi OS NVR version from RSS")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error getting latest UniFi OS NVR version from RSS: {str(e)}")
        return None
    except Exception as e:
        print(f"Error parsing latest UniFi OS NVR version from RSS: {str(e)}")
        return None


def _is_version_newer(version1, version2):
    try:
        def version_tuple(v):
            return tuple(map(int, (v.split("."))))
        return version_tuple(version1) > version_tuple(version2)
    except:
        return False


def get_unifi_os_version(instance, url):
    from .utils import ssh_get_version
    import re

    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname

    if not hostname:
        print_error(instance, "Could not extract hostname from URL")
        return None

    ssh_target = f"root@{hostname}"

    commands_to_try = [
        "cat /usr/lib/version",
        "cat /etc/unifi-os/version",
        "unifi-os info 2>/dev/null | grep -i version || true"
    ]

    for command in commands_to_try:
        result = ssh_get_version(instance, ssh_target, command)
        if result and result.strip():
            # /usr/lib/version format: UNVR4.al324.v4.4.2.b26bf4a.250901.1127
            version_patterns = [
                r'\.v(\d+\.\d+\.\d+)\.',
                r'(\d+\.\d+\.\d+)',
            ]

            for pattern in version_patterns:
                match = re.search(pattern, result)
                if match:
                    return match.group(1)

    print_error(instance, "Could not determine UniFi OS version via SSH")
    return None
