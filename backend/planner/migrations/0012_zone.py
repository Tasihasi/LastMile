import json
from pathlib import Path

from django.db import migrations, models


def seed_default_zones(apps, schema_editor):
    """Start with the 16 zones from Gergő's sheet (zones.json); planners edit them from then on."""
    Zone = apps.get_model("planner", "Zone")
    path = Path(__file__).resolve().parent.parent / "zones.json"
    for z in json.loads(path.read_text(encoding="utf-8"))["zones"]:
        Zone.objects.get_or_create(code=z["id"], defaults={"name": z.get("name", ""), "zips": list(z["zips"])})


class Migration(migrations.Migration):
    dependencies = [
        ("planner", "0011_stop_delivered_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="Zone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(blank=True, default="", max_length=100)),
                ("zips", models.JSONField(default=list)),
            ],
            options={"ordering": ["code"]},
        ),
        migrations.RunPython(seed_default_zones, migrations.RunPython.noop),
    ]
