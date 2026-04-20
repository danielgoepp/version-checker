import subprocess
from .utils import print_error


def get_samba_version(instance, target):
    try:
        cmd = [
            "ssh",
            "-o", "ConnectTimeout=10",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            instance,
            'smbd --version 2>/dev/null || smbstatus --version 2>/dev/null || rpm -q samba 2>/dev/null || dpkg -l | grep samba | head -1'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            output = result.stdout.strip()

            if output:
                version = parse_samba_version(output)
                if version:
                    print(f"  {instance}: {version}")
                    return version
                else:
                    print_error(instance, f"Could not parse Samba version from: {output}")
                    return None
            else:
                print_error(instance, "No Samba version output received")
                return None
        else:
            error_msg = result.stderr.strip() if result.stderr else "SSH command failed"
            print_error(instance, f"SSH failed: {error_msg}")
            return None

    except subprocess.TimeoutExpired:
        print_error(instance, "SSH timeout")
        return None
    except Exception as e:
        print_error(instance, f"SSH error: {str(e)}")
        return None


def parse_samba_version(output):
    import re

    patterns = [
        r'Version\s+(\d+\.\d+\.\d+)',
        r'samba\s+(\d+\.\d+\.\d+)',
        r'samba.*?(\d+\.\d+\.\d+)',
        r'(\d+\.\d+\.\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def get_latest_samba_version(target_host):
    if not target_host:
        return 'No updates'

    try:
        return check_for_samba_updates(target_host)
    except Exception as e:
        print(f"  Error checking Samba updates: {e}")
        return 'No updates'


def check_for_samba_updates(target_host):
    try:
        print(f"    Checking for Samba updates on {target_host}...")

        cmd = [
            'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
            target_host, 'apt', 'list', '--upgradable'
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if any(pkg in line.lower() for pkg in ['samba', 'smbd', 'nmbd', 'winbind']):
                    print("    Found Samba update available")
                    return 'update available'

            return 'No updates'

        return 'No updates'

    except Exception as e:
        print(f"  Error getting Samba updates via SSH: {e}")
        return 'No updates'
