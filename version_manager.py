#!/usr/bin/env python

from datetime import datetime
import re
import sys
import urllib3
from pathlib import Path

import yaml

urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

from src.checkers.github import get_github_latest_version, get_github_latest_tag
from src.checkers.home_assistant import get_home_assistant_version
from src.checkers.esphome import get_esphome_version
from src.checkers.music_assistant import get_music_assistant_version
from src.checkers.konnected import get_konnected_version, get_konnected_current_version
from src.checkers.airgradient import (
    get_airgradient_version,
    get_airgradient_current_version,
)
from src.checkers.opnsense import get_opnsense_version
from src.checkers.k3s import get_k3s_current_version
from src.checkers.zigbee2mqtt import get_zigbee2mqtt_version
from src.checkers.kopia import get_kopia_version
from src.checkers.kubectl import (
    get_telegraf_version,
    get_mosquitto_version,
    get_victoriametrics_version,
    get_calico_version,
    get_metallb_version,
    get_alertmanager_version,
    get_fluentbit_version,
    get_mongodb_version,
    get_opensearch_version,
    get_pgadmin_version,
    get_unpoller_version,
    get_certmanager_version,
    get_postfix_version,
    get_minio_kubectl_version,
    get_minio_operator_version,
)
from src.checkers.cnpg import get_cnpg_version, get_cnpg_postgres_latest_version
from src.checkers.server_status import check_server_status
from src.checkers.proxmox import get_proxmox_version, get_proxmox_latest_version
from src.checkers.tailscale import check_tailscale_versions
from src.checkers.traefik import get_traefik_version
from src.checkers.graylog import (
    get_graylog_current_version,
    get_graylog_latest_version_from_repo,
    get_postgresql_latest_version_from_ghcr,
)
from src.checkers.grafana import get_grafana_version
from src.checkers.mongodb import get_mongodb_latest_version
from src.checkers.unifi_protect import (
    get_unifi_protect_version,
    get_unifi_protect_latest_version,
)
from src.checkers.unifi_network import (
    get_unifi_network_version,
    get_unifi_network_latest_version,
)
from src.checkers.unifi_os import get_unifi_os_nvr_latest_version, get_unifi_os_version
from src.checkers.samba import get_samba_version, get_latest_samba_version
from src.checkers.syncthing import check_syncthing_current_version
from src.checkers.awx import check_awx_current_version
from src.checkers.graylog_compat import get_opensearch_compatible_version
from src.checkers.postfix import get_postfix_latest_version_from_dockerhub
from src.checkers.dockerhub import (
    get_dockerhub_latest_version,
    get_dockerhub_latest_beta,
)
from src.checkers.n8n import get_n8n_version_api, get_n8n_version_kubectl
from src.checkers.openclaw import get_openclaw_version
from src.checkers.wyoming import (
    get_wyoming_openwakeword_version,
    get_wyoming_piper_version,
    get_wyoming_whisper_version,
    get_wyoming_satellite_version,
)
from src.checkers.ollama import get_ollama_version
from src.checkers.docker import get_docker_version
from src.checkers.portainer import get_portainer_version
from src.checkers.open_webui import get_open_webui_version
from src.checkers.vault import get_vault_version as get_vault_kubectl_version, get_vault_k8s_version, restart_vault_pod
from src.checkers.uptime_kuma import (
    get_uptime_kuma_version as get_uptime_kuma_api_version,
)
from src.checkers.upgrade import trigger_awx_upgrade, trigger_awx_apt_upgrade, trigger_awx_llm_upgrade, trigger_vault_unseal, update_manifest_version, update_helm_values_version, git_commit_push_manifest, kubectl_apply_manifest, AWX_UPGRADE_METHODS, MANIFEST_UPGRADE_METHODS, HELM_UPGRADE_METHODS, CR_UPGRADE_METHODS
import config


FIELD_MAP = {
    "Name": "name",
    "Enabled": "enabled",
    "Context": "context",
    "Namespace": "namespace",
    "Instance": "instance",
    "Type": "type",
    "Category": "category",
    "Version_Pin": "version_pin",
    "Upgrade": "upgrade",
    "Target": "target",
    "Esphome_Key": "esphome key",
    "GitHub": "github",
    "DockerHub": "dockerhub",
    "Current_Version": "current_version",
    "Latest_Version": "latest_version",
    "Status": "status",
    "Last_Checked": "last_checked",
    "Last_Upgraded": "last_upgraded",
    "Check_Current": "check_current",
    "Check_Latest": "check_latest",
    "Helm_Values_File": "helm_values_file",
    "Extra_Manifests": "extra_manifests",
}
YAML_TO_FIELD = {v: k for k, v in FIELD_MAP.items()}


def _parse_note(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return {"frontmatter": {}, "body": content, "path": path}
    end = content.find("\n---\n", 4)
    if end == -1:
        return {"frontmatter": {}, "body": content, "path": path}
    frontmatter = yaml.safe_load(content[4:end]) or {}
    body = content[end + 5:]
    return {"frontmatter": frontmatter, "body": body, "path": path}


def _write_note(note: dict) -> None:
    yaml_text = yaml.dump(
        note["frontmatter"],
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )
    note["path"].write_text(
        f"---\n{yaml_text}---\n",
        encoding="utf-8",
    )


class VersionManager:
    STATUS_ICONS = {
        "Up to Date": "✅",
        "Update Available": "⚠️ ",
        "Latest Available": "📋",
        "Current Version": "📌",
        "Unknown": "❓",
    }

    DEFAULT_VAULT_FOLDER = Path(
        getattr(config, "OBSIDIAN_VAULT_FOLDER", "/Users/dang/Documents/Goeppedia/Software")
    )

    def __init__(self, vault_folder=None):
        self.vault_folder = Path(vault_folder) if vault_folder else self.DEFAULT_VAULT_FOLDER
        self.notes = []
        self.load_vault()

    def load_vault(self):
        md_files = sorted(self.vault_folder.glob("*.md"))
        self.notes = [_parse_note(p) for p in md_files]
        enabled = sum(1 for n in self.notes if n["frontmatter"].get("enabled", True) is True)
        print(f"Loaded {len(self.notes)} applications from Obsidian vault ({enabled} enabled)")

    def save_workbook(self):
        pass

    def get_row_data(self, idx: int) -> dict:
        fm = self.notes[idx]["frontmatter"]
        data = {}
        for yaml_key, pascal_key in YAML_TO_FIELD.items():
            val = fm.get(yaml_key)
            data[pascal_key] = val if val is not None else ""
        return data

    def update_row_data(self, idx: int, updates: dict) -> None:
        fm = self.notes[idx]["frontmatter"]
        for pascal_key, value in updates.items():
            yaml_key = FIELD_MAP.get(pascal_key)
            if yaml_key:
                fm[yaml_key] = value if value != "" else None
        _write_note(self.notes[idx])

    def find_application_row(self, app_name: str, instance: str = "prod") -> int | None:
        for idx, note in enumerate(self.notes):
            fm = note["frontmatter"]
            if (
                str(fm.get("name", "")).lower() == app_name.lower()
                and str(fm.get("instance", "")).lower() == instance.lower()
            ):
                return idx
        return None

    def find_application_rows_by_name(self, app_name: str, instance: str = "") -> list[int]:
        matches = []
        for idx, note in enumerate(self.notes):
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue
            if str(fm.get("name", "")).lower() != app_name.lower():
                continue
            if instance and str(fm.get("instance", "")).lower() != instance.lower():
                continue
            matches.append(idx)
        return matches

    def get_all_application_names(self) -> list[str]:
        names = set()
        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue
            if fm.get("name"):
                names.add(fm["name"])
        return sorted(names)

    def _get_dockerhub_version_for_app(self, app_name, dockerhub_repo, version_pin=None):
        if version_pin == "beta":
            return get_dockerhub_latest_beta(dockerhub_repo)
        if app_name == "mongodb":
            return get_mongodb_latest_version()
        elif app_name == "graylog":
            if "graylog" in dockerhub_repo.lower():
                return get_graylog_latest_version_from_repo(dockerhub_repo)
            elif "postgres" in dockerhub_repo.lower():
                return get_postgresql_latest_version_from_ghcr(dockerhub_repo)
            elif "postfix" in dockerhub_repo.lower():
                return get_postfix_latest_version_from_dockerhub(dockerhub_repo)
            else:
                return get_dockerhub_latest_version(dockerhub_repo)
        elif app_name == "minio":
            return get_dockerhub_latest_version(
                dockerhub_repo,
                version_pattern=r"^RELEASE\.(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)(?:-[a-z0-9]+)?$",
                exclude_tags=["latest"],
            )
        else:
            return get_dockerhub_latest_version(dockerhub_repo)

    def _get_github_version_for_app(self, app_name, github_repo, check_latest):
        if app_name == "mongodb" and github_repo == "mongodb/mongo":
            return get_mongodb_latest_version()
        elif check_latest == "github_release":
            return get_github_latest_version(github_repo)
        elif check_latest == "github_tag":
            return get_github_latest_tag(github_repo)
        return None

    def get_latest_version(self, app_name, check_latest, github_repo, dockerhub_repo, version_pin=None):
        latest_version = None

        if check_latest == "github_release" or check_latest == "github_tag":
            if github_repo and github_repo.strip():
                if app_name == "konnected":
                    latest_version = get_konnected_version("latest", None, github_repo)
                elif app_name == "airgradient":
                    latest_version = get_airgradient_version("latest", None, github_repo)
                else:
                    latest_version = self._get_github_version_for_app(
                        app_name, github_repo, check_latest
                    )
        elif check_latest == "docker_hub":
            if dockerhub_repo and dockerhub_repo.strip():
                if app_name == "cnpg" and "postgres-containers" in dockerhub_repo:
                    latest_version = get_cnpg_postgres_latest_version()
                else:
                    latest_version = self._get_dockerhub_version_for_app(
                        app_name, dockerhub_repo, version_pin
                    )
        elif check_latest == "proxmox":
            latest_version = get_proxmox_latest_version(include_ceph=True)
        elif check_latest == "unifi_protect_rss":
            if app_name == "ui-protect":
                latest_version = get_unifi_protect_latest_version()
        elif check_latest == "unifi_network_rss":
            if app_name == "ui-network":
                latest_version = get_unifi_network_latest_version()
        elif check_latest == "unifi_os_nvr_rss":
            latest_version = get_unifi_os_nvr_latest_version()
        elif check_latest == "graylog_compat":
            latest_version = get_opensearch_compatible_version()
        elif check_latest == "helm_search":
            if github_repo and github_repo.strip():
                from src.checkers.utils import get_helm_search_app_version
                latest_version = get_helm_search_app_version(github_repo, app_name)
        elif check_latest == "helm_chart":
            if app_name == "mongodb":
                from src.checkers.utils import get_helm_chart_version
                latest_version = get_helm_chart_version(
                    "mongodb/helm-charts", "community-operator", "operator.version"
                )
            elif app_name == "fluent-bit":
                from src.checkers.utils import get_helm_chart_app_version
                latest_version = get_helm_chart_app_version(
                    "fluent/helm-charts", "fluent-bit"
                )

        return latest_version

    def get_current_version(self, app_data):
        app_name = app_data.get("Name", "")
        instance = app_data.get("Instance", "prod")
        check_current = app_data.get("Check_Current", "")
        check_latest = app_data.get("Check_Latest", "")
        url = app_data.get("Target", "")
        github_repo = app_data.get("GitHub", "")
        context = app_data.get("Context", "") or None
        namespace = app_data.get("Namespace", "") or None

        current_version = None
        latest_version = None
        firmware_update_available = False

        if check_current == "api":
            if app_name == "homeassistant":
                if url:
                    current_version = get_home_assistant_version(instance, url)
            elif app_name == "esphome":
                if url:
                    current_version = get_esphome_version(url)
            elif app_name == "konnected":
                current_version = get_konnected_current_version(instance, url)
            elif app_name == "airgradient":
                encryption_key = app_data.get("Esphome_Key", "")
                current_version = get_airgradient_current_version(
                    instance, url, encryption_key
                )
            elif app_name == "traefik":
                current_version = get_traefik_version(instance, url)
            elif app_name == "opnsense":
                result = get_opnsense_version(instance, url)
                if isinstance(result, dict):
                    current_version = result.get("current_version")
                    firmware_update_available = result.get(
                        "firmware_update_available", False
                    )
                    if result.get("full_version"):
                        latest_version = result["full_version"]
            elif app_name == "proxmox":
                if url:
                    current_version = get_proxmox_version(instance, url)
            elif app_name == "tailscale":
                print("  Checking all Tailscale devices...")
                device_results = check_tailscale_versions(
                    api_key=config.TAILSCALE_ACCESS_TOKEN, tailnet=config.TAILSCALE_TAILNET
                )
                if device_results and device_results["total_devices"] > 0:
                    devices_needing_updates = device_results["devices_needing_updates"]
                    devices_up_to_date = device_results["devices_up_to_date"]
                    current_version = f"{devices_needing_updates} need updates"
                    latest_version = f"{devices_up_to_date} up-to-date"
            elif app_name == "graylog":
                if url:
                    current_version = get_graylog_current_version(instance, url)
            elif app_name == "ui-protect":
                if url:
                    current_version = get_unifi_protect_version(instance, url)
            elif app_name == "ui-network":
                if url:
                    current_version = get_unifi_network_version(instance, url)
            elif app_name == "awx":
                if url:
                    current_version = check_awx_current_version(instance, url)
            elif app_name == "syncthing":
                if url:
                    current_version = check_syncthing_current_version(instance, url)
            elif app_name == "n8n":
                if url:
                    current_version = get_n8n_version_api(instance, url)
            elif app_name == "ollama":
                if url:
                    current_version = get_ollama_version(instance, url)
            elif app_name == "portainer":
                if url:
                    current_version = get_portainer_version(instance, url)
            elif app_name == "openwebui":
                if url:
                    current_version = get_open_webui_version(instance, url)
            elif app_name == "uptime-kuma":
                current_version = get_uptime_kuma_api_version(instance, url)
            elif app_name == "music-assistant":
                if url:
                    current_version = get_music_assistant_version(instance, url)

        elif check_current == "ssh":
            if check_latest == "ssh_apt":
                kernel_result = check_server_status(instance, url)
                if isinstance(kernel_result, dict):
                    current_version = kernel_result.get("current_version")
                    latest_version = kernel_result.get("latest_version")
            else:
                if app_name == "unifi-os":
                    if url:
                        current_version = get_unifi_os_version(instance, url)

        elif check_current == "kubectl":
            if app_name == "telegraf":
                current_version = get_telegraf_version(instance, context=context, namespace=namespace)
            elif app_name == "victoriametrics":
                current_version = get_victoriametrics_version(instance, context=context, namespace=namespace)
            elif app_name == "mosquitto":
                current_version = get_mosquitto_version(instance, context=context, namespace=namespace)
            elif app_name == "calico":
                current_version = get_calico_version(instance, context=context, namespace=namespace)
            elif app_name == "metallb":
                current_version = get_metallb_version(instance, context=context, namespace=namespace)
            elif app_name == "alertmanager":
                current_version = get_alertmanager_version(instance, context=context, namespace=namespace)
            elif app_name == "fluent-bit":
                current_version = get_fluentbit_version(instance, context=context, namespace=namespace)
            elif app_name == "mongodb":
                current_version = get_mongodb_version(instance, context=context, namespace=namespace)
            elif app_name == "opensearch":
                current_version = get_opensearch_version(instance, context=context, namespace=namespace)
            elif app_name == "cnpg":
                current_version = get_cnpg_version(instance, context=context, namespace=namespace)
            elif app_name == "pgadmin":
                current_version = get_pgadmin_version(instance, context=context, namespace=namespace)
            elif app_name == "grafana":
                current_version = get_grafana_version(instance, context=context, namespace=namespace)
            elif app_name == "unpoller":
                current_version = get_unpoller_version(instance, context=context, namespace=namespace)
            elif app_name == "cert-manager":
                current_version = get_certmanager_version(instance, context=context, namespace=namespace)
            elif app_name == "k3s":
                current_version = get_k3s_current_version(instance, context=context)
            elif app_name == "postfix":
                current_version = get_postfix_version(instance, context=context, namespace=namespace)
            elif app_name == "minio":
                if instance == "operator":
                    current_version = get_minio_operator_version(instance, context=context, namespace=namespace)
                else:
                    current_version = get_minio_kubectl_version(instance, context=context, namespace=namespace)
            elif app_name == "n8n":
                current_version = get_n8n_version_kubectl(instance, context=context, namespace=namespace)
            elif app_name == "openclaw":
                current_version = get_openclaw_version(instance, context=context, namespace=namespace)
            elif app_name == "vault":
                if instance == "k8s":
                    current_version = get_vault_k8s_version(instance, context=context, namespace=namespace)
                else:
                    current_version = get_vault_kubectl_version(instance, context=context, namespace=namespace)
            elif app_name == "rhasspy" and instance == "wyoming-openwakeword":
                current_version = get_wyoming_openwakeword_version(instance, url)
            elif app_name == "rhasspy" and instance == "wyoming-piper":
                current_version = get_wyoming_piper_version(instance, url)
            elif app_name == "rhasspy" and instance == "wyoming-whisper":
                current_version = get_wyoming_whisper_version(instance, url)

        elif check_current == "mqtt":
            if app_name == "zigbee2mqtt":
                current_version = get_zigbee2mqtt_version(instance)

        elif check_current == "command":
            if app_name == "kopia":
                current_version = get_kopia_version(instance, url)
            elif app_name == "samba":
                current_version = get_samba_version(instance, url)
                if check_latest == "ssh_apt":
                    latest_version = get_latest_samba_version(instance)
            elif app_name == "docker":
                current_version = get_docker_version(instance, url)
            elif app_name == "wyoming-satellite":
                current_version = get_wyoming_satellite_version(instance, url)

        return current_version, latest_version, firmware_update_available

    def check_single_application(self, idx: int):
        app_data = self.get_row_data(idx)
        app_name = app_data.get("Name", "")
        instance = app_data.get("Instance", "prod")
        check_current = app_data.get("Check_Current", "")
        check_latest = app_data.get("Check_Latest", "")
        github_repo = app_data.get("GitHub", "")
        dockerhub_repo = app_data.get("DockerHub", "")

        print(f"Checking {app_name} ({instance})...")

        if app_name == "unifi-os" and check_latest == "unifi_os_nvr_rss":
            current_version, ssh_latest_version, firmware_update_available = (
                self.get_current_version(app_data)
            )
            latest_version = get_unifi_os_nvr_latest_version(current_version)
        elif check_latest == "proxmox":
            current_version, ssh_latest_version, firmware_update_available = (
                self.get_current_version(app_data)
            )
            latest_version = get_proxmox_latest_version(
                include_ceph=True, current_version=current_version
            )
        else:
            version_pin = app_data.get("Version_Pin", "")
            latest_version = self.get_latest_version(
                app_name, check_latest, github_repo, dockerhub_repo, version_pin
            )
            current_version, ssh_latest_version, firmware_update_available = (
                self.get_current_version(app_data)
            )

        if ssh_latest_version:
            latest_version = ssh_latest_version

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates = {"Last_Checked": timestamp}
        updates["Current_Version"] = current_version if current_version else ""
        updates["Latest_Version"] = latest_version if latest_version else ""

        if firmware_update_available:
            updates["Notes"] = "Firmware update available"

        status = "Unknown"
        if current_version and latest_version:
            if check_current == "api" and app_name == "tailscale":
                if "0 need updates" in current_version:
                    status = "Up to Date"
                else:
                    status = "Update Available"
            elif check_current == "ssh" and check_latest == "ssh_apt":
                if latest_version == "No updates":
                    status = "Up to Date"
                else:
                    status = "Update Available"
            else:
                current_clean = current_version
                if "build:" in current_version:
                    current_clean = current_version.split("build:")[0].strip()

                latest_clean = latest_version
                if latest_clean.startswith("v"):
                    latest_clean = latest_clean[1:]

                if current_clean == latest_clean:
                    status = "Up to Date"
                else:
                    status = "Update Available"
        elif latest_version and not current_version:
            status = "Latest Available"
        elif current_version and not latest_version:
            status = "Current Version"

        updates["Status"] = status
        self.update_row_data(idx, updates)

        current_display = current_version if current_version else "N/A"
        latest_display = latest_version if latest_version else "N/A"
        icon = self.STATUS_ICONS.get(status, "")

        print(f"  Current: {current_display}")
        print(f"  Latest: {latest_display}")
        print(f"  Status: {icon} {status}")
        print()

        return f"{app_name} ({instance})" if not current_version else None

    def check_all_applications(self):
        print("Starting version check for all applications...")
        print("=" * 50)

        enabled_indices = []
        skipped = 0
        for idx, note in enumerate(self.notes):
            if note["frontmatter"].get("enabled", True) is True:
                enabled_indices.append(idx)
            else:
                skipped += 1

        total_apps = len(enabled_indices)
        if skipped > 0:
            print(f"Skipping {skipped} disabled applications")
        print(f"Checking {total_apps} enabled applications...")
        print()

        unavailable = []
        for idx in enabled_indices:
            label = self.check_single_application(idx)
            if label:
                unavailable.append(label)

        print("=" * 50)
        print(f"Version check completed! Checked {total_apps} applications.")

        if unavailable:
            print(f"\n❓ Current version unavailable for {len(unavailable)} application(s):")
            for label in unavailable:
                print(f"  {label}")

    def show_summary(self):
        print("\nVersion Summary (Enabled Applications):")
        print("=" * 40)

        status_counts = {}
        total_apps = 0
        disabled_apps = 0

        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                disabled_apps += 1
                continue
            status = fm.get("status") or "Unknown"
            status_counts[status] = status_counts.get(status, 0) + 1
            total_apps += 1

        for status, count in status_counts.items():
            icon = self.STATUS_ICONS.get(status, "")
            print(f"{icon} {status}: {count}")

        print(f"\nTotal Enabled Applications: {total_apps}")
        if disabled_apps > 0:
            print(f"Disabled Applications: {disabled_apps}")

        print(f"\n⚠️  Applications needing updates:")
        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue
            if fm.get("status") != "Update Available":
                continue
            name = fm.get("name", "")
            instance = fm.get("instance", "")
            current = fm.get("current_version", "N/A") or "N/A"
            latest = fm.get("latest_version", "N/A") or "N/A"
            app_display = f"{name}-{instance}" if instance != "prod" else name
            print(f"  {app_display}: {current} -> {latest}")

    def show_applications(self):
        all_data = []
        max_widths = {
            "index": 4,
            "name": len("Name"),
            "instance": len("Instance"),
            "current": len("Current"),
            "latest": len("Latest"),
            "status": 3,
        }

        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue

            name = str(fm.get("name", ""))
            instance = str(fm.get("instance", ""))
            current = str(fm.get("current_version", "") or "")
            latest = str(fm.get("latest_version", "") or "")
            status = str(fm.get("status", "") or "")

            max_widths["name"] = max(max_widths["name"], len(name))
            max_widths["instance"] = max(max_widths["instance"], len(instance))
            max_widths["current"] = max(max_widths["current"], len(current))
            max_widths["latest"] = max(max_widths["latest"], len(latest))

            all_data.append({"name": name, "instance": instance, "current": current, "latest": latest, "status": status})

        total_width = sum(max_widths.values()) + len(max_widths) * 2

        print("\nApplications:")
        print("=" * total_width)
        print(
            f"{'#':<{max_widths['index']}} {'Name':<{max_widths['name']}} {'Instance':<{max_widths['instance']}} {'Current':<{max_widths['current']}} {'Latest':<{max_widths['latest']}} {'':<{max_widths['status']}}"
        )
        print("-" * total_width)

        for index, data in enumerate(all_data):
            status_icon = self.STATUS_ICONS.get(data["status"], "") if data["status"] else ""
            print(
                f"{index:<{max_widths['index']}} {data['name']:<{max_widths['name']}} {data['instance']:<{max_widths['instance']}} {data['current']:<{max_widths['current']}} {data['latest']:<{max_widths['latest']}} {status_icon:<{max_widths['status']}}"
            )

        print(f"\nTotal: {len(all_data)} applications")

    def show_updates(self):
        updates = []
        max_widths = {
            "index": 4,
            "name": len("Name"),
            "instance": len("Instance"),
            "current": len("Current"),
            "latest": len("Latest"),
            "status": 3,
        }

        for note in self.notes:
            fm = note["frontmatter"]
            if fm.get("enabled", True) is not True:
                continue
            if fm.get("status") != "Update Available":
                continue

            name = str(fm.get("name", ""))
            instance = str(fm.get("instance", ""))
            current = str(fm.get("current_version", "") or "")
            latest = str(fm.get("latest_version", "") or "")

            max_widths["name"] = max(max_widths["name"], len(name))
            max_widths["instance"] = max(max_widths["instance"], len(instance))
            max_widths["current"] = max(max_widths["current"], len(current))
            max_widths["latest"] = max(max_widths["latest"], len(latest))

            updates.append({"name": name, "instance": instance, "current": current, "latest": latest, "status": "Update Available"})

        total_width = sum(max_widths.values()) + len(max_widths) * 2

        print("\nApplications Needing Updates:")
        print("=" * total_width)
        print(
            f"{'#':<{max_widths['index']}} {'Name':<{max_widths['name']}} {'Instance':<{max_widths['instance']}} {'Current':<{max_widths['current']}} {'Latest':<{max_widths['latest']}} {'':<{max_widths['status']}}"
        )
        print("-" * total_width)

        for index, data in enumerate(updates):
            status_icon = self.STATUS_ICONS.get(data["status"], "")
            print(
                f"{index:<{max_widths['index']}} {data['name']:<{max_widths['name']}} {data['instance']:<{max_widths['instance']}} {data['current']:<{max_widths['current']}} {data['latest']:<{max_widths['latest']}} {status_icon:<{max_widths['status']}}"
            )

        print(f"\nTotal: {len(updates)} applications")

    def upgrade_application(self, app_name: str, dry_run: bool = False, instance: str = "", force: bool = False):
        matching = self.find_application_rows_by_name(app_name, instance=instance)

        if not matching:
            print(f"Application '{app_name}' not found")
            return

        launched = 0
        manifests_updated = 0
        skipped = 0

        for idx in matching:
            app_data = self.get_row_data(idx)
            instance = app_data.get("Instance", "prod")
            version_pin = app_data.get("Version_Pin", "") or ""
            upgrade_method = app_data.get("Upgrade", "") or ""
            status = app_data.get("Status", "") or ""
            label = f"{app_name} ({instance})"

            if not force and status == "Up to Date":
                print(f"  Skipping {label}: already up to date")
                skipped += 1
                continue

            if upgrade_method == "ansible-apt":
                print(f"  Upgrading {label} via AWX (method: {upgrade_method})...")
                success = trigger_awx_apt_upgrade(instance, instance, dry_run=dry_run)
                if success:
                    launched += 1
                    if not dry_run:
                        self.update_row_data(idx, {"Last_Upgraded": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                else:
                    skipped += 1
                continue

            if upgrade_method == "ansible-llm":
                print(f"  Upgrading {label} via AWX (method: {upgrade_method})...")
                success = trigger_awx_llm_upgrade(app_name, instance, dry_run=dry_run)
                if success:
                    launched += 1
                    if not dry_run:
                        self.update_row_data(idx, {"Last_Upgraded": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                else:
                    skipped += 1
                continue

            if version_pin == "latest":
                if upgrade_method not in AWX_UPGRADE_METHODS:
                    print(f"  Skipping {label}: upgrade method '{upgrade_method}' is not supported")
                    skipped += 1
                    continue
                print(f"  Upgrading {label} via AWX (method: {upgrade_method})...")
                awx_key = f"{app_name}-{instance}"
                success = trigger_awx_upgrade(awx_key, instance, dry_run=dry_run)
                if success:
                    launched += 1
                    if not dry_run:
                        self.update_row_data(idx, {"Last_Upgraded": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                else:
                    skipped += 1
                continue

            if version_pin == "pinned":
                if upgrade_method not in AWX_UPGRADE_METHODS and upgrade_method not in CR_UPGRADE_METHODS:
                    print(f"  Skipping {label}: upgrade method '{upgrade_method}' is not supported")
                    skipped += 1
                    continue

                if upgrade_method in CR_UPGRADE_METHODS:
                    context = app_data.get("Context", "") or ""
                    namespace = app_data.get("Namespace", "") or ""
                    manifest_rel = f"{app_name}/manifests/{app_name}-{instance}.yaml"
                    extra_manifests = app_data.get("Extra_Manifests") or []

                    if not force:
                        current_version = app_data.get("Current_Version", "") or ""
                        latest_version = app_data.get("Latest_Version", "") or ""
                        print(f"  Updating manifest for {label}...")
                        manifest_ok = update_manifest_version(
                            manifest_rel, current_version, latest_version, dry_run=dry_run
                        )
                        if not manifest_ok:
                            skipped += 1
                            continue

                        for extra_rel in extra_manifests:
                            print(f"  Updating extra manifest {extra_rel}...")
                            update_manifest_version(extra_rel, current_version, latest_version, dry_run=dry_run)

                        print(f"  Committing and pushing manifests for {label}...")
                        push_ok = git_commit_push_manifest(
                            manifest_rel, app_name, latest_version, dry_run=dry_run,
                            extra_rel_paths=extra_manifests,
                        )
                        if not push_ok:
                            skipped += 1
                            continue

                        manifests_updated += 1
                    else:
                        print(f"  Skipping manifest update for {label} (--force)")

                    print(f"  Applying manifest for {label}...")
                    apply_ok = kubectl_apply_manifest(manifest_rel, context, namespace, instance, dry_run=dry_run)
                    if apply_ok:
                        launched += 1
                        if not dry_run:
                            self.update_row_data(idx, {"Last_Upgraded": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    else:
                        skipped += 1
                    continue

                if upgrade_method in MANIFEST_UPGRADE_METHODS and not force:
                    current_version = app_data.get("Current_Version", "") or ""
                    latest_version = app_data.get("Latest_Version", "") or ""
                    manifest_rel = f"{app_name}/manifests/{app_name}-{instance}.yaml"

                    print(f"  Updating manifest for {label}...")
                    manifest_ok = update_manifest_version(
                        manifest_rel, current_version, latest_version, dry_run=dry_run
                    )
                    if not manifest_ok:
                        skipped += 1
                        continue

                    print(f"  Committing and pushing manifest for {label}...")
                    push_ok = git_commit_push_manifest(
                        manifest_rel, app_name, latest_version, dry_run=dry_run
                    )
                    if not push_ok:
                        skipped += 1
                        continue

                    manifests_updated += 1
                elif upgrade_method in MANIFEST_UPGRADE_METHODS and force:
                    print(f"  Skipping manifest update for {label} (--force)")

                elif upgrade_method in HELM_UPGRADE_METHODS and not force:
                    current_version = app_data.get("Current_Version", "") or ""
                    latest_version = app_data.get("Latest_Version", "") or ""
                    helm_values_file = app_data.get("Helm_Values_File", "") or ""

                    if not helm_values_file:
                        print(f"  Skipping {label}: helm_values_file not set in note")
                        skipped += 1
                        continue

                    print(f"  Updating helm values for {label}...")
                    values_ok = update_helm_values_version(
                        helm_values_file, current_version, latest_version, dry_run=dry_run
                    )
                    if not values_ok:
                        skipped += 1
                        continue

                    print(f"  Committing and pushing helm values for {label}...")
                    push_ok = git_commit_push_manifest(
                        helm_values_file, app_name, latest_version, dry_run=dry_run
                    )
                    if not push_ok:
                        skipped += 1
                        continue

                    manifests_updated += 1
                elif upgrade_method in HELM_UPGRADE_METHODS and force:
                    print(f"  Skipping helm values update for {label} (--force)")

                if upgrade_method in AWX_UPGRADE_METHODS:
                    print(f"  Triggering AWX upgrade for {label} (method: {upgrade_method})...")
                    awx_key = f"{app_name}-{instance}"
                    success = trigger_awx_upgrade(awx_key, instance, dry_run=dry_run)

                    if success and app_name == "vault" and instance == "prod":
                        context = app_data.get("Context", "") or None
                        namespace = app_data.get("Namespace", "") or None
                        print(f"  Restarting vault pod for {label}...")
                        pod_ok = restart_vault_pod(instance, context=context, namespace=namespace, dry_run=dry_run)
                        if pod_ok:
                            print(f"  Triggering vault unseal for {label}...")
                            trigger_vault_unseal(instance, dry_run=dry_run)

                    if success:
                        launched += 1
                        if not dry_run:
                            self.update_row_data(idx, {"Last_Upgraded": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
                    else:
                        skipped += 1
                continue

            print(f"  Skipping {label}: version_pin '{version_pin}' not handled by --upgrade")
            skipped += 1

        print()
        if dry_run:
            print(f"[DRY RUN] Would have updated {manifests_updated} manifest(s), triggered {launched} upgrade(s), skipped {skipped}")
        else:
            print(f"Updated {manifests_updated} manifest(s), triggered {launched} upgrade(s), skipped {skipped}")


if __name__ == "__main__":
    print("Use check_versions.py to interact with the version checker.")
    print("Run: ./check_versions.py --help")
