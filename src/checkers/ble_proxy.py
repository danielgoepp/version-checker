from .utils import print_error, print_version


def get_ble_proxy_version(instance, url=None):
    if not url:
        print_error(instance, "No device URL configured")
        return None

    try:
        import asyncio
        import aioesphomeapi
        from urllib.parse import urlparse

        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        if not hostname:
            print_error(instance, "Could not parse hostname from URL")
            return None

        async def get_device_info():
            try:
                api = aioesphomeapi.APIClient(hostname, 6053, "")
                await api.connect(login=False)
                device_info = await api.device_info()
                await api.disconnect()
                if hasattr(device_info, "esphome_version") and device_info.esphome_version:
                    return device_info.esphome_version
                return None
            except Exception as e:
                return f"Error: {str(e)}"

        try:
            version = asyncio.run(get_device_info())

            if version and not version.startswith("Error:"):
                print_version(instance, f"ESPHome version: {version}")
                return version
            elif version:
                print_error(instance, version)
                return None
            else:
                print_error(instance, "No ESPHome version found in device response")
                return None

        except Exception as e:
            print_error(instance, f"ESPHome API error: {str(e)}")
            return None

    except ImportError:
        print_error(instance, "aioesphomeapi module not available")
        return None
