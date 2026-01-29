"""Uptime Kuma version checker using Socket.IO API"""

from .utils import print_version, print_error


def get_uptime_kuma_version(instance, url):
    """Get Uptime Kuma version via the uptime_kuma_api library"""
    try:
        from uptime_kuma_api import UptimeKumaApi
        import config

        username = config.UPTIME_KUMA_USERNAME
        password = config.UPTIME_KUMA_PASSWORD

        if not all([url, username, password]):
            print_error(instance, "Uptime Kuma URL or credentials not configured")
            return None

        api = UptimeKumaApi(url)
        api.login(username, password)
        info = api.info()
        api.disconnect()

        version = info.get("version")
        if version:
            print_version(instance, version)
            return version

        print_error(instance, "No version field in Uptime Kuma info response")
        return None

    except Exception as e:
        print_error(instance, f"Failed to get Uptime Kuma version: {e}")
        return None
