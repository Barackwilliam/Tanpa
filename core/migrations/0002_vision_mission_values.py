"""Fill TANPA's official vision, mission and core values (only where still empty)."""

from django.db import migrations

VISION = (
    "Advancing safe, equitable and high-quality anaesthesia and perioperative care "
    "in Tanzania and beyond."
)
MISSION = (
    "Strengthening anaesthesia professionals through education, research, advocacy, "
    "leadership and strategic partnerships to improve patient safety and quality of care."
)
VALUES = "\n".join([
    "Patient Safety", "Professionalism", "Excellence", "Integrity",
    "Teamwork", "Equity", "Innovation", "Leadership",
])


def fill(apps, schema_editor):
    SiteSettings = apps.get_model("core", "SiteSettings")
    s, _ = SiteSettings.objects.get_or_create(pk=1)
    changed = []
    if not s.vision.strip():
        s.vision = VISION
        changed.append("vision")
    if not s.mission.strip():
        s.mission = MISSION
        changed.append("mission")
    if not s.core_values.strip():
        s.core_values = VALUES
        changed.append("core_values")
    if changed:
        s.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
