from .base import APIChecker


def get_music_assistant_version(instance, url):
    checker = APIChecker(instance, url)
    return checker.get_json_api_version("info", version_field="server_version")
