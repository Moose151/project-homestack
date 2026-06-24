"""backups services — create and restore backups (D17).

The low-level operations (_dump_db, _tar_media, _restore_db, _unpack_media) are
isolated so tests can patch them without running pg_dump against an SQLite test DB.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from apps.accounts.models import User
    from apps.backups.models import Backup


def _backup_dir() -> Path:
    return Path(getattr(settings, "BACKUP_DIR", settings.BASE_DIR / "backups"))


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _dump_db(dest: Path) -> None:
    """Run pg_dump in custom format to dest."""
    db = settings.DATABASES["default"]
    env = {**os.environ, "PGPASSWORD": db.get("PASSWORD", "")}
    subprocess.run(
        [
            "pg_dump",
            "-h", db.get("HOST", "localhost"),
            "-p", str(db.get("PORT", 5432)),
            "-U", db.get("USER", ""),
            "-d", db.get("NAME", ""),
            "-F", "c",
            "-f", str(dest),
        ],
        env=env,
        check=True,
        capture_output=True,
    )


def _tar_media(dest: Path) -> None:
    """Tar the Django MEDIA_ROOT into dest."""
    media_root = Path(getattr(settings, "MEDIA_ROOT", settings.BASE_DIR / "media"))
    with tarfile.open(dest, "w:gz") as tar:
        if media_root.exists():
            tar.add(media_root, arcname="media")


def _restore_db(src: Path) -> None:
    """Restore a pg_dump custom-format file into the configured DB."""
    db = settings.DATABASES["default"]
    env = {**os.environ, "PGPASSWORD": db.get("PASSWORD", "")}
    subprocess.run(
        [
            "pg_restore",
            "-h", db.get("HOST", "localhost"),
            "-p", str(db.get("PORT", 5432)),
            "-U", db.get("USER", ""),
            "-d", db.get("NAME", ""),
            "--clean", "--if-exists", "--no-owner",
            str(src),
        ],
        env=env,
        check=True,
        capture_output=True,
    )


def _unpack_media(src: Path) -> None:
    """Unpack a media tarball, overwriting MEDIA_ROOT."""
    media_root = Path(getattr(settings, "MEDIA_ROOT", settings.BASE_DIR / "media"))
    media_root.mkdir(parents=True, exist_ok=True)
    with tarfile.open(src, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name.startswith("media/"):
                member.name = member.name[len("media/"):]
            if member.name:
                tar.extract(member, path=media_root)


def create_backup(user: "User") -> "Backup":
    """Create a pg_dump + media tarball backup, record it, and log an audit entry.

    Raises on failure (status is set to FAILED before re-raising).
    """
    from apps.audit.helpers import log_audit
    from apps.backups.models import Backup
    from apps.core.models import get_active_household

    household = get_active_household()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = f"backup_{timestamp}"

    backup = Backup.objects.create(
        household=household,
        label=label,
        status=Backup.Status.RUNNING,
        created_by=user,
        updated_by=user,
    )

    try:
        backup_path = _backup_dir() / label
        backup_path.mkdir(parents=True, exist_ok=True)

        db_file = backup_path / "db.dump"
        media_file = backup_path / "media.tar.gz"

        _dump_db(db_file)
        _tar_media(media_file)

        backup.db_file = f"{label}/db.dump"
        backup.media_file = f"{label}/media.tar.gz"
        backup.db_checksum = _sha256(db_file)
        backup.media_checksum = _sha256(media_file)
        backup.size_bytes = db_file.stat().st_size + media_file.stat().st_size
        backup.status = Backup.Status.COMPLETE
        backup.updated_by = user
        backup.save()

        log_audit(
            "backup_created",
            user=user,
            target_record_type="backups.Backup",
            target_record_id=backup.id,
        )

    except Exception as exc:
        backup.status = Backup.Status.FAILED
        backup.error_message = str(exc)
        backup.updated_by = user
        backup.save()
        raise

    return backup


def restore_backup(backup: "Backup", user: "User") -> None:
    """Restore a completed backup. Verifies checksums, runs pg_restore + media unpack.

    Raises ValueError on checksum mismatch or non-COMPLETE backup.
    Raises subprocess.CalledProcessError on pg_restore failure.
    """
    from apps.audit.helpers import log_audit
    from apps.backups.models import Backup

    if backup.status != Backup.Status.COMPLETE:
        raise ValueError("Only COMPLETE backups can be restored.")

    backup_path = _backup_dir() / backup.label
    db_file = backup_path / "db.dump"
    media_file = backup_path / "media.tar.gz"

    if backup.db_checksum and _sha256(db_file) != backup.db_checksum:
        raise ValueError("DB dump checksum mismatch — backup may be corrupted.")
    if backup.media_checksum and _sha256(media_file) != backup.media_checksum:
        raise ValueError("Media tarball checksum mismatch — backup may be corrupted.")

    _restore_db(db_file)
    _unpack_media(media_file)

    log_audit(
        "backup_restored",
        user=user,
        target_record_type="backups.Backup",
        target_record_id=backup.id,
    )
