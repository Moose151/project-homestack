"""Permission-first tests for the shared attachment service (D10/D11)."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.attachments.models import Attachment
from apps.audit.models import AuditLog
from apps.core.models import get_active_household


def _make_user(username: str, role: str, *, child: bool = False) -> User:
    user = User.objects.create_user(
        username=username,
        display_name=username.title(),
        role=role,
        password="testpass!",
        is_child_account=child,
    )
    user.set_pin("1234")
    user.save()
    return user


@override_settings(ATTACHMENT_MAX_BYTES=1024)
class AttachmentAPITests(TestCase):
    """The API must never rely on the client to hide attachment metadata or files."""

    def setUp(self):
        self.media_root = tempfile.mkdtemp(prefix="homestack-attachments-")
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)

        self.household = get_active_household()
        self.admin = _make_user("admin", User.Role.ADMIN)
        self.manager = _make_user("manager", User.Role.MANAGER)
        self.member = _make_user("member", User.Role.USER)
        self.other = _make_user("other", User.Role.USER)
        self.guest = _make_user("guest", User.Role.GUEST)
        self.child = _make_user("child", User.Role.USER, child=True)
        self.list_url = reverse("attachment-list")

    def _upload(
        self,
        user: User,
        *,
        name: str = "receipt.txt",
        content: bytes = b"household receipt",
        visibility: str = "household",
        sensitivity: str = "normal",
        linked_record_type: str = "",
        linked_record_id: int | None = None,
    ):
        self.client.force_login(user)
        data = {
            "file": SimpleUploadedFile(name, content, content_type="text/plain"),
            "visibility": visibility,
            "sensitivity": sensitivity,
            "linked_record_type": linked_record_type,
        }
        if linked_record_id is not None:
            data["linked_record_id"] = linked_record_id
        return self.client.post(self.list_url, data)

    def _reauth(self, user: User):
        self.client.force_login(user)
        return self.client.post(
            reverse("auth-reauth"),
            {"password": "testpass!"},
            content_type="application/json",
        )

    def test_anonymous_user_cannot_list_attachments(self):
        self.assertIn(self.client.get(self.list_url).status_code, {401, 403})

    def test_member_can_upload_normal_attachment(self):
        response = self._upload(self.member)

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["original_filename"], "receipt.txt")
        self.assertEqual(body["uploaded_by"], self.member.id)
        self.assertEqual(body["file_size"], len(b"household receipt"))
        self.assertEqual(len(body["checksum"]), 64)
        self.assertNotIn("file_path", body)
        self.assertFalse(any(Path(self.media_root).rglob("*receipt.txt")))

    def test_guest_and_child_cannot_upload(self):
        self.assertEqual(self._upload(self.guest).status_code, 403)
        self.assertEqual(self._upload(self.child).status_code, 403)

    def test_oversized_upload_is_rejected(self):
        response = self._upload(self.member, content=b"x" * 1025)
        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.json())

    def test_link_type_and_id_must_be_supplied_together(self):
        response = self._upload(
            self.member,
            linked_record_type="homestead.InsurancePolicy",
        )
        self.assertEqual(response.status_code, 400)

    def test_private_attachment_is_visible_only_to_owner_and_adults(self):
        attachment_id = self._upload(
            self.member,
            visibility="private",
        ).json()["id"]

        self.client.force_login(self.other)
        self.assertNotIn(attachment_id, [item["id"] for item in self.client.get(self.list_url).json()])
        self.client.force_login(self.manager)
        self.assertIn(attachment_id, [item["id"] for item in self.client.get(self.list_url).json()])

    def test_sensitive_metadata_is_hidden_until_password_reauth(self):
        attachment_id = self._upload(
            self.admin,
            visibility="sensitive",
            sensitivity="financial",
        ).json()["id"]

        self.client.force_login(self.admin)
        self.assertNotIn(attachment_id, [item["id"] for item in self.client.get(self.list_url).json()])
        self._reauth(self.admin)
        self.assertIn(attachment_id, [item["id"] for item in self.client.get(self.list_url).json()])

    def test_child_never_sees_sensitive_household_attachment(self):
        attachment_id = self._upload(
            self.admin,
            visibility="household",
            sensitivity="document",
        ).json()["id"]

        self.client.force_login(self.child)
        self.assertNotIn(attachment_id, [item["id"] for item in self.client.get(self.list_url).json()])

    def test_normal_download_streams_file(self):
        attachment_id = self._upload(self.member).json()["id"]
        self.client.force_login(self.other)

        response = self.client.get(reverse("attachment-download", args=[attachment_id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"household receipt")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_storage_path_is_not_served_as_public_media(self):
        attachment_id = self._upload(self.member).json()["id"]
        attachment = Attachment.objects.get(pk=attachment_id)

        self.assertEqual(self.client.get(f"/media/{attachment.file_path.name}").status_code, 404)

    def test_sensitive_download_requires_reauth_and_is_audited(self):
        attachment_id = self._upload(
            self.admin,
            name="statement.pdf",
            content=b"financial statement",
            visibility="sensitive",
            sensitivity="financial",
        ).json()["id"]
        url = reverse("attachment-download", args=[attachment_id])

        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 403)
        self._reauth(self.admin)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        audit = AuditLog.objects.get(
            action="sensitive_attachment_downloaded",
            target_record_id=attachment_id,
        )
        self.assertEqual(audit.user, self.admin)

    def test_member_can_soft_delete_own_attachment(self):
        attachment_id = self._upload(self.member).json()["id"]
        self.client.force_login(self.member)

        response = self.client.delete(reverse("attachment-detail", args=[attachment_id]))

        self.assertEqual(response.status_code, 204)
        self.assertFalse(any(item["id"] == attachment_id for item in self.client.get(self.list_url).json()))

    def test_member_cannot_delete_another_users_attachment(self):
        attachment_id = self._upload(self.member).json()["id"]
        self.client.force_login(self.other)

        response = self.client.delete(reverse("attachment-detail", args=[attachment_id]))

        self.assertEqual(response.status_code, 403)

    def test_manager_can_delete_another_users_attachment(self):
        attachment_id = self._upload(self.member).json()["id"]
        self.client.force_login(self.manager)

        self.assertEqual(
            self.client.delete(reverse("attachment-detail", args=[attachment_id])).status_code,
            204,
        )

    def test_filters_by_linked_record(self):
        kept_id = self._upload(
            self.member,
            linked_record_type="home_wiki.WikiPage",
            linked_record_id=10,
        ).json()["id"]
        self._upload(
            self.member,
            linked_record_type="home_wiki.WikiPage",
            linked_record_id=11,
        )
        self.client.force_login(self.member)

        response = self.client.get(
            self.list_url,
            {"linked_record_type": "home_wiki.WikiPage", "linked_record_id": 10},
        )

        self.assertEqual([item["id"] for item in response.json()], [kept_id])
