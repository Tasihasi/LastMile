"""Build the street list the parser corrects against, from a TSV exported from the OSM Hungary extract.

Input lines: ``<postal code or settlement>\t<street name>`` (for example from
``osmium export`` / Overpass, one street per line). Output: JSON for ``ADDRESS_STREETS_FILE``.
Budapest zips (1DDx) are grouped by district; everything else by folded settlement name.

    python manage.py build_street_index streets.tsv streets_hu_osm.json

Data is OpenStreetMap (ODbL): keep the attribution when the file is redistributed.
"""

import json
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError

from planner.addressparse.data import is_budapest_zip
from planner.addressparse.fold import fold


class Command(BaseCommand):
    help = "Convert a '<zip or settlement><TAB><street>' list into the parser's street index (JSON)."

    def add_arguments(self, parser):
        parser.add_argument("source")
        parser.add_argument("target")

    def handle(self, *args, **options):
        budapest: dict[str, set] = defaultdict(set)
        towns: dict[str, set] = defaultdict(set)
        count = 0
        try:
            with open(options["source"], encoding="utf-8") as fh:
                for line in fh:
                    if "\t" not in line:
                        continue
                    area, street = (p.strip() for p in line.rstrip("\n").split("\t", 1))
                    if not area or not street:
                        continue
                    if is_budapest_zip(area):
                        budapest[str(int(area[1:3]))].add(street)
                    elif not area.isdigit():
                        towns[fold(area)].add(street)
                    else:
                        continue
                    count += 1
        except OSError as e:
            raise CommandError(str(e)) from e
        out = {"budapest": {k: sorted(v) for k, v in budapest.items()}}
        out.update({k: sorted(v) for k, v in towns.items()})
        with open(options["target"], "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        self.stdout.write(self.style.SUCCESS(f"{count} streets written to {options['target']}"))
