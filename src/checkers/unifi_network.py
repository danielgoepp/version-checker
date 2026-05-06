import requests
from .utils import print_error, handle_timeout_error, handle_generic_error
import config


GRAPHQL_URL = "https://community.svc.ui.com/graphql"
GRAPHQL_HEADERS = {"Content-Type": "application/json"}


def _get_latest_community_version(title):
    query = '{"query":"query { releases(limit: 20, searchTerm: \\"' + title + '\\") { items { title slug } } }"}'
    try:
        response = requests.post(GRAPHQL_URL, data=query, headers=GRAPHQL_HEADERS, timeout=15)
        response.raise_for_status()
        items = response.json()["data"]["releases"]["items"]
        match = next((item for item in items if item["title"] == title), None)
        if not match:
            return None
        slug = match["slug"]
        prefix = title.replace(" ", "-") + "-"
        version_hyphenated = slug[len(prefix):]
        return version_hyphenated.replace("-", ".")
    except Exception:
        return None


def get_unifi_network_latest_version():
    return _get_latest_community_version("UniFi Network Application")


def get_unifi_os_server_latest_version():
    return _get_latest_community_version("UniFi OS Server")


UOS_HOST_ID = "fc90f597-c8fb-40f8-b6da-7efa1147cb70"


def get_unifi_os_server_version(instance, url):
    if not config.UNIFI_NETWORK_API_KEY:
        print_error(instance, "No UniFi Network API key configured")
        return None

    headers = {
        "X-API-KEY": config.UNIFI_NETWORK_API_KEY,
        "Accept": "application/json",
    }

    try:
        response = requests.get("https://api.ui.com/v1/hosts", headers=headers, timeout=15)
        response.raise_for_status()

        api_response = response.json()
        hosts_data = api_response['data'] if isinstance(api_response, dict) and 'data' in api_response else api_response

        host = next((h for h in hosts_data if h.get('id') == UOS_HOST_ID), None)
        if not host:
            print_error(instance, f"UniFi OS Server host {UOS_HOST_ID} not found in cloud API")
            return None

        firmware_version = (
            host.get('reportedState', {})
                .get('hardware', {})
                .get('firmwareVersion')
        )

        if firmware_version:
            return str(firmware_version)

        print_error(instance, "firmwareVersion not found in reportedState.hardware")
        return None

    except requests.exceptions.RequestException as e:
        print_error(instance, f"UniFi cloud API error: {str(e)}")
        return None
    except Exception as e:
        return handle_generic_error(instance, str(e), "cloud API call")


def get_unifi_network_version(instance, url):
    if not config.UNIFI_NETWORK_API_KEY:
        print_error(instance, "No UniFi Network API key configured")
        return None

    headers = {
        "X-API-KEY": config.UNIFI_NETWORK_API_KEY,
        "Accept": "application/json",
    }

    try:
        response = requests.get("https://api.ui.com/v1/hosts", headers=headers, timeout=15)
        response.raise_for_status()

        api_response = response.json()
        hosts_data = api_response['data'] if isinstance(api_response, dict) and 'data' in api_response else api_response

        host = next((h for h in hosts_data if h.get('id') == UOS_HOST_ID), None)
        if not host:
            print_error(instance, f"UniFi host {UOS_HOST_ID} not found in cloud API")
            return None

        controllers = host.get('reportedState', {}).get('controllers', [])
        network_controller = next((c for c in controllers if c.get('name') == 'network'), None)
        if not network_controller:
            print_error(instance, "Network controller not found in reportedState.controllers")
            return None

        version = network_controller.get('version')
        if version:
            return str(version)

        print_error(instance, "version not found in network controller")
        return None

    except requests.exceptions.RequestException as e:
        print_error(instance, f"UniFi cloud API error: {str(e)}")
        return None
    except Exception as e:
        return handle_generic_error(instance, str(e), "cloud API call")
