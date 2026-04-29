import os
import shutil
import subprocess
from app.config import settings

BLOCKED_FILE = "data/blocked_domains.txt"


def read_blocked_domains() -> list:
    if not os.path.exists(BLOCKED_FILE):
        return []
    with open(BLOCKED_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]


def write_blocked_domains(domains: list):
    os.makedirs(os.path.dirname(BLOCKED_FILE), exist_ok=True)
    with open(BLOCKED_FILE, "w") as f:
        f.write("\n".join(domains))


def apply_hosts_block(domains: list):
    hosts_file = settings.USAGE_HOSTS_FILE
    backup_file = settings.USAGE_BACKUP_FILE
    marker_start = "# >>> BITFISCAL BLOCK START <<<"
    marker_end = "# >>> BITFISCAL BLOCK END <<<"

    if os.geteuid() != 0:
        print("AVISO: root necessário para editar /etc/hosts")
        return

    shutil.copyfile(hosts_file, backup_file)
    with open(hosts_file, "r") as f:
        lines = f.readlines()

    new_lines = []
    inside = False
    for line in lines:
        if marker_start in line:
            inside = True
            continue
        if marker_end in line:
            inside = False
            continue
        if not inside:
            new_lines.append(line)

    new_lines.append(f"{marker_start}\n")
    for d in domains:
        new_lines.append(f"0.0.0.0 {d}\n")
        new_lines.append(f"0.0.0.0 www.{d}\n")
    new_lines.append(f"{marker_end}\n")

    with open(hosts_file, "w") as f:
        f.writelines(new_lines)

    try:
        subprocess.run(
            ["systemctl", "restart", "systemd-resolved"], capture_output=True
        )
    except:
        pass
