#!/usr/bin/env python

import subprocess

_STATUS_NO_UPDATE = 'No updates'


def is_kernel_only_update(latest_version):
    # latest_version from get_latest_linux_kernel_version is "N packages" or
    # "N packages + kernel". Kernel-only means zero real packages with a pending
    # kernel update — nothing for `apt upgrade` to do (the new kernel is held back).
    return (latest_version or "").strip() == "0 packages + kernel"


def get_latest_linux_kernel_version(current_kernel, target_host):
    # Failures return None (status becomes "Current Version"), never
    # "No updates" — an unreachable host must not look up to date.
    if not target_host:
        return None
    try:
        return _check_apt_upgradable(target_host, current_kernel)
    except Exception as e:
        print(f"  Error checking apt updates: {e}")
        return None


def _check_apt_upgradable(target_host, current_kernel):
    print(f"    Checking for apt updates on {target_host}...")

    # Ubuntu delivers kernel updates as new versioned packages installed via the
    # linux-image-generic metapackage — they never appear in apt list --upgradable.
    # We detect them by comparing the metapackage's Depends to the running kernel.
    # RPi kernels upgrade in-place and DO appear in apt list --upgradable.
    remote_cmd = (
        'sudo -n apt-get update -q > /dev/null 2>&1; '
        'apt list --upgradable 2>/dev/null; '
        'echo "===KERNEL==="; '
        'apt-cache show linux-image-generic 2>/dev/null '
        '| grep "^Depends:" | grep -o \'linux-image-[0-9][^, ]*\' | head -1'
    )

    cmd = [
        'ssh', '-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=no',
        target_host, remote_cmd
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        print(f"    apt check on {target_host} failed: {result.stderr.strip()}")
        return None

    parts = result.stdout.split('===KERNEL===\n', 1)
    pkg_lines = [l for l in parts[0].splitlines() if l and not l.startswith('Listing')]
    kernel_section = parts[1].strip() if len(parts) > 1 else ''

    count = len(pkg_lines)
    kernel_update = _has_kernel_update(pkg_lines, kernel_section, current_kernel)

    if count == 0 and not kernel_update:
        return _STATUS_NO_UPDATE

    suffix = ' + kernel' if kernel_update else ''
    return f"{count} packages{suffix}"


def _has_kernel_update(pkg_lines, kernel_section, current_kernel):
    # RPi: kernel packages upgrade in-place and appear directly in apt list --upgradable
    if any('raspberrypi-kernel' in l or 'linux-image-rpi-' in l for l in pkg_lines):
        return True

    # LXC containers share the Proxmox host kernel (-pve suffix); they can't update it
    if current_kernel and current_kernel.endswith('-pve'):
        return False

    # Ubuntu: compare the kernel the metapackage depends on vs the running kernel
    # kernel_section is e.g. "linux-image-6.8.0-110-generic"
    if kernel_section and current_kernel:
        latest_kernel = kernel_section.replace('linux-image-', '')  # "6.8.0-110-generic"
        return latest_kernel != current_kernel

    return False
