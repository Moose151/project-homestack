"""Backup tests — Phase 1.11.

Covers:
- Permissions: only admin can view/create/restore.
- Create: reauth gate, happy path (mocked ops), failure sets FAILED status.
- Restore: reauth gate, 404, checksum mismatch, happy path (mocked ops).
- Download: returns a tar.gz stream.
- Service: restore rejects non-COMPLETE backups.
"""
import hashlib
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.backups.models import Backup
from apps.backups import services
from apps.core.models import get_active_household


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _make_user(username, role=User.Role.ADMIN, password="testpass!"):
    u = User.objects.create_user(
        username=username, display_name=username.capitalize(), role=role, password=password,
    )
    u.set_pin("1234")
    u.save()
    return u


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"),
        {"username": username, "pin": pin},
        content_type="application/json",
    )


def _reauth(client, password="testpass!"):
    client.post(
        reverse("auth-reauth"),
        {"password": password},
        content_type="application/json",
    )


def _make_complete_backup(tmpdir: str, admin: User) -> Backup:
    """Create a COMPLETE Backup record with real files in tmpdir."""
    label = "backup_test"
    backup_path = Path(tmpdir) / label
    backup_path.mkdir()
    db_file = backup_path / "db.dump"
    media_file = backup_path / "media.tar.gz"
    db_file.write_bytes(b"fake-db-dump-data")
    media_file.write_bytes(b"fake-media-tarball")
    return Backup.objects.create(
        household=get_active_household(),
        label=label,
        status=Backup.Status.COMPLETE,
        db_file=f"{label}/db.dump",
        media_file=f"{label}/media.tar.gz",
        db_checksum=_sha256(db_file),
        media_checksum=_sha256(media_file),
        size_bytes=db_file.stat().st_size + media_file.stat().st_size,
        created_by=admin,
        updated_by=admin,
    )


# ---------------------------------------------------------------------------
# Permission tests
# ---------------------------------------------------------------------------

class BackupPermissionTests(TestCase):

    def setUp(self):
        self.admin = _make_user("admin_u")
        self.manager = _make_user("manager_u", role=User.Role.MANAGER, password="mgrpass!")
        self.user = _make_user("regular_u", role=User.Role.USER, password="userpass!")
        self.url = reverse("backup-list")

    def test_unauthenticated_cannot_list(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_manager_cannot_list(self):
        _login(self.client, "manager_u")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_user_cannot_list(self):
        _login(self.client, "regular_u")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_admin_can_list_empty(self):
        _login(self.client, "admin_u")
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])


# ---------------------------------------------------------------------------
# Create tests
# ---------------------------------------------------------------------------

class BackupCreateTests(TestCase):

    def setUp(self):
        self.admin = _make_user("admin_u")
        self.url = reverse("backup-list")
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_create_without_reauth_returns_403(self):
        _login(self.client, "admin_u")
        resp = self.client.post(self.url, {}, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_create_with_reauth_returns_201(self):
        _login(self.client, "admin_u")
        _reauth(self.client)

        def _fake_dump(dest):
            dest.write_bytes(b"fake-db-dump-data")

        def _fake_tar(dest):
            dest.write_bytes(b"fake-media-tarball")

        with patch.object(services, "_backup_dir", return_value=Path(self.tmpdir)), \
             patch.object(services, "_dump_db", side_effect=_fake_dump), \
             patch.object(services, "_tar_media", side_effect=_fake_tar):
            resp = self.client.post(self.url, {}, content_type="application/json")

        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["status"], "complete")
        self.assertTrue(data["label"].startswith("backup_"))
        self.assertEqual(Backup.objects.filter(status=Backup.Status.COMPLETE).count(), 1)

    def test_create_records_checksums_and_size(self):
        _login(self.client, "admin_u")
        _reauth(self.client)
        db_content = b"db-content"
        media_content = b"media-content"

        def _fake_dump(dest):
            dest.write_bytes(db_content)

        def _fake_tar(dest):
            dest.write_bytes(media_content)

        with patch.object(services, "_backup_dir", return_value=Path(self.tmpdir)), \
             patch.object(services, "_dump_db", side_effect=_fake_dump), \
             patch.object(services, "_tar_media", side_effect=_fake_tar):
            resp = self.client.post(self.url, {}, content_type="application/json")

        data = resp.json()
        expected_db = hashlib.sha256(db_content).hexdigest()
        expected_media = hashlib.sha256(media_content).hexdigest()
        self.assertEqual(data["db_checksum"], expected_db)
        self.assertEqual(data["media_checksum"], expected_media)
        self.assertEqual(data["size_bytes"], len(db_content) + len(media_content))

    def test_create_failure_sets_failed_status(self):
        with patch.object(services, "_backup_dir", return_value=Path(self.tmpdir)), \
             patch.object(services, "_dump_db", side_effect=RuntimeError("pg_dump failed")):
            with self.assertRaises(RuntimeError):
                services.create_backup(self.admin)

        backup = Backup.objects.first()
        self.assertIsNotNone(backup)
        self.assertEqual(backup.status, Backup.Status.FAILED)
        self.assertIn("pg_dump failed", backup.error_message)


# ---------------------------------------------------------------------------
# Restore tests
# ---------------------------------------------------------------------------

class BackupRestoreTests(TestCase):

    def setUp(self):
        self.admin = _make_user("admin_u")
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_restore_without_reauth_returns_403(self):
        _login(self.client, "admin_u")
        backup = _make_complete_backup(self.tmpdir, self.admin)
        url = reverse("backup-restore", args=[backup.id])
        resp = self.client.post(url, {}, content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_restore_nonexistent_returns_404(self):
        _login(self.client, "admin_u")
        _reauth(self.client)
        url = reverse("backup-restore", args=[99999])
        resp = self.client.post(url, {}, content_type="application/json")
        self.assertEqual(resp.status_code, 404)

    def test_restore_db_checksum_mismatch_raises(self):
        backup = _make_complete_backup(self.tmpdir, self.admin)
        backup.db_checksum = "a" * 64   # wrong
        backup.save()

        with patch.object(services, "_backup_dir", return_value=Path(self.tmpdir)):
            with self.assertRaises(ValueError) as ctx:
                services.restore_backup(backup, self.admin)
        self.assertIn("checksum mismatch", str(ctx.exception))

    def test_restore_non_complete_backup_raises(self):
        backup = Backup.objects.create(
            household=get_active_household(),
            label="backup_fail",
            status=Backup.Status.FAILED,
            created_by=self.admin,
            updated_by=self.admin,
        )
        with self.assertRaises(ValueError) as ctx:
            services.restore_backup(backup, self.admin)
        self.assertIn("COMPLETE", str(ctx.exception))

    def test_restore_success_calls_restore_ops(self):
        _login(self.client, "admin_u")
        _reauth(self.client)
        backup = _make_complete_backup(self.tmpdir, self.admin)
        url = reverse("backup-restore", args=[backup.id])

        with patch.object(services, "_backup_dir", return_value=Path(self.tmpdir)), \
             patch.object(services, "_restore_db") as mock_db, \
             patch.object(services, "_unpack_media") as mock_media:
            resp = self.client.post(url, {}, content_type="application/json")

        self.assertEqual(resp.status_code, 200)
        mock_db.assert_called_once()
        mock_media.assert_called_once()

    def test_non_admin_cannot_restore(self):
        manager = _make_user("mgr_u", role=User.Role.MANAGER, password="mgrpass!")
        _login(self.client, "mgr_u")
        _reauth(self.client, password="mgrpass!")
        backup = _make_complete_backup(self.tmpdir, self.admin)
        url = reverse("backup-restore", args=[backup.id])
        resp = self.client.post(url, {}, content_type="application/json")
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# Download test
# ---------------------------------------------------------------------------

class BackupDownloadTests(TestCase):

    def setUp(self):
        self.admin = _make_user("admin_u")
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_download_returns_tar_stream(self):
        _login(self.client, "admin_u")
        backup = _make_complete_backup(self.tmpdir, self.admin)
        url = reverse("backup-download", args=[backup.id])

        with patch.object(services, "_backup_dir", return_value=Path(self.tmpdir)):
            resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/x-tar")
        self.assertIn(f"{backup.label}.tar.gz", resp["Content-Disposition"])

    def test_download_nonexistent_returns_404(self):
        _login(self.client, "admin_u")
        url = reverse("backup-download", args=[99999])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)
