from .utils import http_get, print_error, print_version

def get_konnected_current_version(instance, url=None):
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

        async def get_esphome_device_info():
            try:
                api = aioesphomeapi.APIClient(hostname, 6053, "")
                await api.connect(login=False)

                device_info = await api.device_info()
                await api.disconnect()

                esphome_version = None
                library_version = None

                if hasattr(device_info, 'esphome_version') and device_info.esphome_version:
                    esphome_version = device_info.esphome_version

                if hasattr(device_info, 'project_version') and device_info.project_version:
                    library_version = device_info.project_version

                return {"esphome_version": esphome_version, "library_version": library_version}

            except Exception as e:
                return f"Error: {str(e)}"

        try:
            result = asyncio.run(get_esphome_device_info())

            if isinstance(result, str) and result.startswith("Error:"):
                print_error(instance, result)
                return None
            elif isinstance(result, dict):
                esphome_version = result.get("esphome_version")
                library_version = result.get("library_version")
                if esphome_version:
                    print_version(instance, f"ESPHome: {esphome_version}, Library: {library_version}")
                    return result
                else:
                    print_error(instance, "No ESPHome version found in device response")
                    return None
            else:
                print_error(instance, "No version info found in device response")
                return None

        except Exception as e:
            print_error(instance, f"ESPHome API error: {str(e)}")
            return None

    except ImportError:
        print_error(instance, "aioesphomeapi module not available")
        return None

def get_konnected_version(instance, url=None, github_repo=None):
    if not github_repo:
        print_error(instance, "No GitHub repository configured")
        return None

    github_url = f"https://raw.githubusercontent.com/{github_repo}/master/garage-door-GDOv2-Q.yaml"
    yaml_content = http_get(github_url)
    if yaml_content and isinstance(yaml_content, str):
        for line in yaml_content.split('\n'):
            if line.strip().startswith('project_version:'):
                version = line.split(':', 1)[1].strip().strip('"\'')
                print_version(instance, version)
                return version

    print_error(instance, "Could not get project version")
    return None
