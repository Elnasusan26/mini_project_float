from models import db, Room, Class, TimetableEntry
from utils.normalize import normalize_slot


def allocate_rooms():

    print("\n========== ALLOCATOR START ==========")

    floating_entries = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.room_id == None,
        TimetableEntry.is_lab_hour == False
    ).all()

    permanent_rooms = Room.query.filter_by(is_permanent=True).all()
    occupied = set()

    for e in TimetableEntry.query.filter(TimetableEntry.room_id != None):
        occupied.add((e.day, normalize_slot(e.slot), e.room_id))

    for entry in floating_entries:
        entry.slot = normalize_slot(entry.slot)
        cls = Class.query.get(entry.class_id)

        for room in permanent_rooms:
            if room.capacity < cls.strength:
                continue

            lab_free = TimetableEntry.query.filter_by(
                class_id=room.owner_class_id,
                day=entry.day,
                slot=entry.slot,
                is_lab_hour=True
            ).first()

            if not lab_free:
                continue

            key = (entry.day, entry.slot, room.id)
            if key in occupied:
                continue

            entry.room_id = room.id
            occupied.add(key)

            print(f"✔ Allocated | {cls.name} | {entry.day} {entry.slot} | {room.name}")
            break

    db.session.commit()
