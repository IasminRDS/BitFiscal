import subprocess
import platform
import socket
import time
from sqlalchemy.orm import Session
from app.models import MonitorHost
from app.config import settings


def ping_host(host: str, timeout: float = 2.0) -> tuple[bool, int]:
    """Retorna (alcançável, tempo em ms)."""
    param = "-n" if platform.system().lower() == "windows" else "-c"
    cmd = ["ping", param, "1", "-W", str(int(timeout)), host]
    try:
        start = time.time()
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 1
        )
        elapsed = int((time.time() - start) * 1000)
        return result.returncode == 0, elapsed
    except:
        return False, None


def check_service(host: str, port: int, timeout: float = 2.0) -> tuple[bool, int]:
    """Verifica se a porta TCP está aberta."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    start = time.time()
    try:
        sock.connect((host, port))
        elapsed = int((time.time() - start) * 1000)
        sock.close()
        return True, elapsed
    except:
        return False, None


def atualizar_todos_hosts(db: Session):
    """Percorre todos os MonitorHost cadastrados e atualiza status."""
    hosts = db.query(MonitorHost).all()
    for host in hosts:
        ok, ms = ping_host(host.ip)
        host.status = "online" if ok else "offline"
        host.ultimo_ping_ms = ms if ok else 0
        if not ok:
            host.falhas_consecutivas += 1
        else:
            host.falhas_consecutivas = 0
    db.commit()
