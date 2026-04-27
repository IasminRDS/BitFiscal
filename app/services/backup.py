from datetime import datetime


def gerar_status_simples():
    return {
        "status": "ok",
        "detalhe": f"Backup simulado executado em {datetime.utcnow().isoformat()} UTC",
    }
