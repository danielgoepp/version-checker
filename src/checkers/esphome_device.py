import asyncio
import base64
import threading
from urllib.parse import urlparse

import aioesphomeapi
from aioesphomeapi.singleton import _SINGLETON_CACHE
from aioesphomeapi.timezone import _get_local_timezone

from .utils import print_error

_timezone_cache_lock = threading.Lock()


def _prime_esphome_timezone_cache():
    """Work around an aioesphomeapi bug (as of the version pinned in .venv):
    its timezone lookup is memoized in a process-global dict keyed by a fixed
    string, not scoped per event loop. api.connect() awaits it on every call
    (connection.py's _cached_timezone assignment), so when check_all_applications
    runs multiple ESPHome device checks concurrently via ThreadPoolExecutor
    (each worker thread running its own asyncio.run() loop), two threads can
    race to populate the cache: the first plants an asyncio.Future bound to
    its own loop, and the second awaits that same Future from a different
    loop, raising "Future ... attached to a different loop". Priming the
    cache synchronously with the resolved value before any concurrent
    connects happen means every thread finds a plain string already cached,
    never a Future, so the race can't occur.
    """
    with _timezone_cache_lock:
        if "local_timezone" not in _SINGLETON_CACHE:
            _SINGLETON_CACHE["local_timezone"] = _get_local_timezone()


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

    _prime_esphome_timezone_cache()

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
