from .base import APIChecker

def get_esphome_version(url):
    checker = APIChecker("ESPHome", url)

    version = checker.get_json_api_version("version", version_field="version")
    if version:
        return version

    version = checker.get_text_api_version("", r'ESPHome\s+v?(\d+\.\d+\.\d+)')
    if version:
        return version

    print("  ESPHome: Could not get version")
    return None
