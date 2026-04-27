import subprocess
import platform
import time


def ping_host(ip: str) -> tuple[str, int]:
    # Retorna (status, ms)
    param = "-n" if platform.system().lower() == "windows" else "-c"
    cmd = ["ping", param, "1", ip]
    start = time.time()
    try:
        subprocess.run(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2
        )
        ms = int((time.time() - start) * 1000)
        return "online", ms
    except Exception:
        return "offline", 0
