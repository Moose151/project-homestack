"""Generate a VAPID keypair for Web Push (docs/32_Core_Notifications_and_Push.md §10).

Run once per installation, then paste the output into .env. Never commit the private key.
"""
from __future__ import annotations

import base64

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from django.core.management.base import BaseCommand


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


class Command(BaseCommand):
    help = "Generate a fresh VAPID keypair for Web Push and print .env-ready values."

    def handle(self, *args, **options):
        private_key = ec.generate_private_key(ec.SECP256R1())
        public_key = private_key.public_key()

        private_raw = private_key.private_numbers().private_value.to_bytes(32, "big")
        public_raw = public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)

        self.stdout.write(self.style.SUCCESS("Generated a new VAPID keypair. Add these to .env:"))
        self.stdout.write("")
        self.stdout.write(f"VAPID_PUBLIC_KEY={_b64url(public_raw)}")
        self.stdout.write(f"VAPID_PRIVATE_KEY={_b64url(private_raw)}")
        self.stdout.write("VAPID_SUBJECT=mailto:you@yourdomain.example")
        self.stdout.write("")
        self.stdout.write(
            "The private key never leaves the server. Rotating it invalidates every existing "
            "push subscription — households will need to re-enable push on each device."
        )
