import subprocess
import time
from app.config import settings
from app.models import BackupJob
from sqlalchemy.orm import Session


def executar_backups(db: Session):
    """Executa rsync para cada origem em BACKUP_SOURCE_DIRS."""
    sources = [s.strip() for s in settings.BACKUP_SOURCE_DIRS.split(",") if s.strip()]
    dest = settings.BACKUP_DEST_DIR
    opts = settings.RSYNC_OPTIONS.split()
    for src in sources:
        start = time.time()
        cmd = ["rsync"] + opts + [src, dest]
        status = "ok"
        detalhe = ""
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if proc.returncode != 0:
                status = "falha"
                detalhe = proc.stderr or proc.stdout
            else:
                detalhe = "Backup concluído"
        except Exception as e:
            status = "falha"
            detalhe = str(e)
        duration = int(time.time() - start)
        job = BackupJob(
            alvo=src, status=status, detalhe=detalhe[:500], duration_seconds=duration
        )
        db.add(job)
    db.commit()
