import requests
from .utils import print_error, handle_timeout_error, handle_generic_error
import config


def get_unifi_network_latest_version():
    try:
        import xml.etree.ElementTree as ET
        import re

        rss_url = "https://community.ui.com/rss/releases/UniFi-Network-Application/e6712595-81bb-4829-8e42-9e2630fabcfe"

        headers = {
            'Accept': 'application/rss+xml, application/xml, text/xml',
            'User-Agent': 'Version Checker 1.0'
        }

        response = requests.get(rss_url, headers=headers, timeout=15, verify=True)

        if response.status_code == 200:
            root = ET.fromstring(response.content)

            items = root.findall('.//item')
            if items:
                first_item = items[0]
                title = first_item.find('title')
                if title is not None:
                    title_text = title.text
                    version_match = re.search(r'UniFi Network Application\s+([\d.]+)', title_text)
                    if version_match:
                        return version_match.group(1)

        return None

    except requests.exceptions.Timeout:
        print("Timeout getting latest UniFi Network version from RSS")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error getting latest UniFi Network version from RSS: {str(e)}")
        return None
    except Exception as e:
        print(f"Error parsing latest UniFi Network version from RSS: {str(e)}")
        return None


def get_unifi_network_version(instance, url):
    if not config.UNIFI_NETWORK_API_KEY:
        print_error(instance, "No UniFi Network API key configured")
        return None

    headers = {
        "X-API-KEY": config.UNIFI_NETWORK_API_KEY,
        "Accept": "application/json",
    }

    try:
        hosts_response = requests.get("https://api.ui.com/v1/hosts", headers=headers, timeout=15)
        hosts_response.raise_for_status()

        api_response = hosts_response.json()

        if isinstance(api_response, dict) and 'data' in api_response:
            hosts_data = api_response['data']
        else:
            hosts_data = api_response

        if not isinstance(hosts_data, list):
            print_error(instance, "Unexpected hosts API response format")
            return None

        target_hostname = None
        if url:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            target_hostname = parsed.hostname

        network_host = None
        for host in hosts_data:
            if host.get('type') == 'network-server':
                network_host = host
                break

        if not network_host:
            print_error(instance, "No UniFi Network host found in cloud API")
            return None

        reported_state = network_host.get('reportedState', {})
        version = (reported_state.get('version') or
                  reported_state.get('firmware_version') or
                  network_host.get('version'))

        if version:
            return str(version)
        else:
            print_error(instance, "Version not found in host information")
            return None

    except requests.exceptions.RequestException as e:
        print_error(instance, f"UniFi cloud API error: {str(e)}")
        return None
    except Exception as e:
        return handle_generic_error(instance, str(e), "cloud API call")
