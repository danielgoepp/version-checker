from .esphome_device import get_esphome_device_info


def get_ble_proxy_version(instance, url=None, encryption_key=None):
    info = get_esphome_device_info(instance, url, encryption_key)
    return info["esphome_version"] if info else None
