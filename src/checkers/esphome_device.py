import asyncio
import base64
from urllib.parse import urlparse

import aioesphomeapi

from .utils import print_error


def _is_valid_base64(s):
    if not s or not s.strip():
        return False
    try:
        base64.b64decode(s.strip(), validate=True)
        return True
    except Exception:
        return False


def get_esphome_device_info(instance, url, encryption_key=None):
    """Read version info from an ESPHome device over the native API.

    Returns {"esphome_version": ..., "library_version": ...} (library_version
    is the device's project_version, None if the firmware doesn't set one),
    or None on any failure.
    """
    if not url:
        print_error(instance, "No device URL configured")
        return None

    hostname = urlparse(url).hostname
    if not hostname:
        print_error(instance, "Could not parse hostname from URL")
        return None

    async def _read():
        if encryption_key and _is_valid_base64(encryption_key):
            api = aioesphomeapi.APIClient(hostname, 6053, password="", noise_psk=encryption_key.strip())
        else:
            api = aioesphomeapi.APIClient(hostname, 6053, "")
        await api.connect(login=False)
        device_info = await api.device_info()
        await api.disconnect()
        return device_info

    try:
        device_info = asyncio.run(_read())
    except Exception as e:
        print_error(instance, f"ESPHome API error: {e}")
        return None

    esphome_version = getattr(device_info, "esphome_version", None) or None
    library_version = getattr(device_info, "project_version", None) or None
    if not esphome_version:
        print_error(instance, "No ESPHome version found in device response")
        return None

    return {"esphome_version": esphome_version, "library_version": library_version}
