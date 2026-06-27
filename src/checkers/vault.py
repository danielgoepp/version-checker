from .kubectl import ImageVersionChecker


def get_vault_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "vault", context=context)
    return checker.get_running_image_version("hashicorp/vault")


def get_vault_k8s_version(instance, context=None, namespace=None):
    checker = ImageVersionChecker(instance, namespace=namespace or "vault", context=context)
    return checker.get_running_image_version("hashicorp/vault-k8s")
