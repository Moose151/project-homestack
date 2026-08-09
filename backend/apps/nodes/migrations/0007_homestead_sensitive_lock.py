"""Record Homestead's finance surface as sensitive, which it always behaved as.

Homestead's costs-and-cover views hard-coded "always require a password", so the lock was real
but invisible to the data model — the household setting that Solace honoured did nothing here.
Now that both nodes share one gate (apps/nodes/access.py), that lock has to be stated rather
than implied, or generalising it would silently unlock the surface.

`supports_sensitive_lock` marks the node as lockable; `requires_reauthentication` turns it on
for this household, matching the behaviour that was already in force. An admin can now turn it
off from Manage, exactly as they can for Money.
"""
from django.db import migrations


def lock_forward(apps, schema_editor):
    Node = apps.get_model("nodes", "Node")
    HouseholdNode = apps.get_model("nodes", "HouseholdNode")

    node = Node.objects.filter(key="homestead").first()
    if node is None:
        return
    node.supports_sensitive_lock = True
    node.save(update_fields=["supports_sensitive_lock", "updated_at"])

    HouseholdNode.objects.filter(node=node).update(requires_reauthentication=True)


def lock_reverse(apps, schema_editor):
    """Leave the lock in place on reverse — removing a password prompt is not a rollback."""


class Migration(migrations.Migration):
    dependencies = [
        ("nodes", "0006_configure_solace_sensitive"),
    ]

    operations = [
        migrations.RunPython(lock_forward, lock_reverse),
    ]
