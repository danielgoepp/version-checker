from .dockerhub import get_dockerhub_latest_version


def get_postfix_latest_version_from_dockerhub(repository):
    return get_dockerhub_latest_version(repository)