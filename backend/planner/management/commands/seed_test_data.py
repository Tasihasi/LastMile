"""Generate test bikers and routes with varied statuses for testing."""

import random
import uuid

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from planner.models import DeliverySession, DeliveryStop, UserProfile

# Budapest area coordinates for realistic test data
BUDAPEST_STOPS = [
    ("Westend City Center", "Vaci ut 1-3, Budapest 1062", 47.5133, 19.0556),
    ("Arena Plaza", "Kerepesi ut 9, Budapest 1087", 47.4985, 19.0985),
    ("MOM Park", "Alkotas u. 53, Budapest 1123", 47.4877, 19.0192),
    ("Corvin Plaza", "Futó utca 37-45, Budapest 1082", 47.4903, 19.0709),
    ("Duna Plaza", "Vaci ut 178, Budapest 1138", 47.5397, 19.0658),
    ("Allee", "Október huszonharmadika u. 8-10, Budapest 1117", 47.4736, 19.0482),
    ("Campona", "Nagytétényi út 37-45, Budapest 1222", 47.4142, 19.0231),
    ("Europark", "Soroksari ut 164, Budapest 1238", 47.4204, 19.0912),
    ("Lurdy Haz", "Könyves Kálmán krt. 12-14, Budapest 1097", 47.4728, 19.0801),
    ("Sugar!", "Örs vezér tere, Budapest 1148", 47.5044, 19.1286),
    ("Mammut", "Lövőház u. 2-6, Budapest 1024", 47.5085, 19.0271),
    ("Árkád", "Örs vezér tere 25, Budapest 1106", 47.5064, 19.1312),
    ("Pólus Center", "Szentmihályi út 131, Budapest 1152", 47.5446, 19.1283),
    ("Budagyöngye", "Szilágyi Erzsébet fasor 121, Budapest 1026", 47.5195, 19.0112),
    ("Central Market", "Vámház krt. 1-3, Budapest 1093", 47.4871, 19.0586),
    ("Lehel Market", "Vaci ut 9-15, Budapest 1134", 47.5201, 19.0635),
    ("Fény Street Market", "Lövőház u. 12, Budapest 1024", 47.5094, 19.0248),
    ("Bosnyák Square Market", "Bosnyák tér, Budapest 1149", 47.5202, 19.1170),
    ("Hold Street Market", "Hold u. 13, Budapest 1054", 47.5058, 19.0495),
    ("Rákóczi Square Market", "Rákóczi tér, Budapest 1084", 47.4924, 19.0740),
]


class Command(BaseCommand):
    help = "Seed test bikers and delivery routes with varied statuses"

    def handle(self, *args, **options):
        # Create bikers
        biker_names = ["Anna", "Balazs", "Csilla"]
        bikers = []
        for name in biker_names:
            user, created = User.objects.get_or_create(username=name)
            if created:
                user.set_unusable_password()
                user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user, defaults={"role": "biker"})
            if profile.role != "biker":
                profile.role = "biker"
                profile.save()
            bikers.append(user)
            self.stdout.write(f"  Biker: {name} (id={user.id})")

        # Ensure planner exists
        planner_user, created = User.objects.get_or_create(username="Planner")
        if created:
            planner_user.set_unusable_password()
            planner_user.save()
        UserProfile.objects.get_or_create(user=planner_user, defaults={"role": "planner"})

        # Route definitions: (name, biker_index, status, stop_count)
        route_defs = [
            # Anna: 1 in_progress, 1 not_started, 1 finished
            ("Anna Morning Route", 0, "in_progress", 6),
            ("Anna Afternoon Route", 0, "not_started", 5),
            ("Anna Yesterday Route", 0, "finished", 4),
            # Balazs: 1 in_progress, 1 not_started
            ("Balazs Downtown Route", 1, "in_progress", 7),
            ("Balazs Suburb Route", 1, "not_started", 5),
            # Csilla: 1 finished, 1 not_started
            ("Csilla Express Route", 2, "finished", 5),
            ("Csilla Evening Route", 2, "not_started", 6),
            # Unassigned
            ("Unassigned Batch 1", None, "not_started", 4),
            ("Unassigned Batch 2", None, "not_started", 3),
        ]

        all_stops = list(BUDAPEST_STOPS)
        random.shuffle(all_stops)
        stop_pool = all_stops * 3  # enough for all routes
        stop_idx = 0

        for route_name, biker_idx, route_status, stop_count in route_defs:
            owner = bikers[biker_idx] if biker_idx is not None else None

            # Create a dummy file
            csv_content = "name,address,lat,lng\n"
            route_stops_data = stop_pool[stop_idx : stop_idx + stop_count]
            stop_idx += stop_count

            for sname, saddr, slat, slng in route_stops_data:
                csv_content += f"{sname},{saddr},{slat},{slng}\n"

            # Generate straight-line geometry from stop coordinates (no ORS needed)
            geometry = {
                "type": "LineString",
                "coordinates": [[slng, slat] for _, _, slat, slng in route_stops_data],
            }

            session = DeliverySession.objects.create(
                id=uuid.uuid4(),
                owner=owner,
                name=route_name,
                original_file=ContentFile(csv_content.encode(), name=f"{route_name.replace(' ', '_')}.csv"),
                total_duration=random.uniform(3600, 10800)
                if route_status != "not_started"
                else random.uniform(3600, 10800),
                total_distance=random.uniform(15000, 50000),
                route_geometry=geometry,
                status=route_status,
                started_at=timezone.now() if route_status in ("in_progress", "finished") else None,
                finished_at=timezone.now() if route_status == "finished" else None,
            )

            # Create stops with sequence orders and delivery statuses
            stops = []
            for seq, (sname, saddr, slat, slng) in enumerate(route_stops_data, start=1):
                delivery_status = "pending"

                if route_status == "finished":
                    # All done — mostly delivered, some not_received
                    delivery_status = random.choices(["delivered", "not_received"], weights=[0.8, 0.2])[0]
                elif route_status == "in_progress":
                    # First ~half delivered, rest pending
                    halfway = stop_count // 2
                    if seq <= halfway:
                        delivery_status = random.choices(["delivered", "not_received"], weights=[0.85, 0.15])[0]

                stops.append(
                    DeliveryStop(
                        session=session,
                        name=sname,
                        raw_address=saddr,
                        lat=slat,
                        lng=slng,
                        geocode_status="skipped",
                        sequence_order=seq,
                        delivery_status=delivery_status,
                    )
                )
            DeliveryStop.objects.bulk_create(stops)

            # Set current_stop_index for in_progress routes
            if route_status == "in_progress":
                first_pending = next((s for s in stops if s.delivery_status == "pending"), None)
                if first_pending:
                    session.current_stop_index = first_pending.sequence_order
                    session.save(update_fields=["current_stop_index"])

            status_label = {"not_started": "[PENDING]", "in_progress": "[ACTIVE]", "finished": "[DONE]"}
            owner_name = owner.username if owner else "Unassigned"
            self.stdout.write(f"  {status_label[route_status]} {route_name} ({stop_count} stops) -> {owner_name}")

        self.stdout.write(self.style.SUCCESS(f"\nCreated {len(route_defs)} test routes for {len(bikers)} bikers"))
