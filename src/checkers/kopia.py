import subprocess
from .utils import print_error, print_version, handle_timeout_error, handle_generic_error

def get_kopia_version(instance, url):
    """Get Kopia version for a specific node instance"""
    if not url or not str(url).startswith(('http://', 'https://')):
        print_error(instance, "No valid URL configured")
        return None

    try:
        # Build command as list for security
        cmd = ["kopia", "server", "status", f"--address={url}", "--version"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)

        if result.returncode == 0:
            raw_version = result.stdout.strip()
            # Clean up the version - extract just the version number
            clean_version = raw_version.split("build:")[0].strip() if "build:" in raw_version else raw_version
            print_version(instance, clean_version)
            return clean_version
        else:
            print_error(instance, "Error retrieving version")
            return None

    except subprocess.TimeoutExpired:
        return handle_timeout_error(instance, "version retrieval")
    except Exception as e:
        return handle_generic_error(instance, e)