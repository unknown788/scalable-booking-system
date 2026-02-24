"""
Production seed script — creates venues, an organizer, and 15 events on NeonDB.
Run from backend/ with venv active:
    python seed_prod.py
"""
import os, sys
from datetime import datetime, timezone, timedelta

# Point at production DB
PROD_DB = (
    "postgresql://neondb_owner:npg_FTL8Mm2dRlXU@ep-old-union-a1rp2g15-pooler"
    ".ap-southeast-1.aws.neon.tech/bookingdb?sslmode=require&channel_binding=require"
)
os.environ["DATABASE_URL"] = PROD_DB

# Make sure app package is importable
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.models.event import Venue, Event, EventType, Seat
from app.models.user import User, UserRole
from app.db.base_class import Base
from app.core.security import get_password_hash

engine = create_engine(PROD_DB, echo=False)
Session = sessionmaker(bind=engine)
db = Session()

# ── 1. Organizer user ──────────────────────────────────────────────────────────
existing = db.query(User).filter_by(email="organizer@bookingapp.dev").first()
if existing:
    organizer = existing
    print(f"Organizer already exists: id={organizer.id}")
else:
    organizer = User(
        full_name="BookingApp Organizer",
        email="organizer@bookingapp.dev",
        hashed_password=get_password_hash("Organizer@123"),
        role=UserRole.organizer,
        is_active=True,
    )
    db.add(organizer)
    db.flush()
    print(f"Created organizer: id={organizer.id}")

# ── 2. Venues ─────────────────────────────────────────────────────────────────
def get_or_create_venue(name, rows, cols):
    v = db.query(Venue).filter_by(name=name).first()
    if v:
        return v
    v = Venue(name=name, rows=rows, cols=cols)
    db.add(v)
    db.flush()
    # create seats with letter rows (A, B, C…) matching event_service.py convention
    for r in range(rows):
        row_letter = chr(65 + r)  # 0→"A", 1→"B", …
        for c in range(1, cols + 1):
            db.add(Seat(row=row_letter, number=c, venue_id=v.id))
    db.flush()
    print(f"  Created venue '{name}' ({rows}x{cols} = {rows*cols} seats) id={v.id}")
    return v

print("\nCreating venues...")
venues = {
    "PVR Cinemas — Hall 1":         get_or_create_venue("PVR Cinemas — Hall 1",         10, 20),   # 200
    "INOX Multiplex — Screen 3":    get_or_create_venue("INOX Multiplex — Screen 3",    12, 18),   # 216
    "Jio World Garden — Mumbai":    get_or_create_venue("Jio World Garden — Mumbai",    20, 30),   # 600
    "Nehru Stadium — Delhi":        get_or_create_venue("Nehru Stadium — Delhi",        25, 40),   # 1000
    "Phoenix Marketcity — Pune":    get_or_create_venue("Phoenix Marketcity — Pune",    15, 25),   # 375
    "The O2 Arena — London":        get_or_create_venue("The O2 Arena — London",        30, 40),   # 1200
    "Madison Square Garden — NYC":  get_or_create_venue("Madison Square Garden — NYC", 30, 50),   # 1500
    "NSCI Dome — Mumbai":           get_or_create_venue("NSCI Dome — Mumbai",           20, 25),   # 500
}

# ── 3. Events ─────────────────────────────────────────────────────────────────
def dt(days_from_now, hour=19):
    return datetime.now(timezone.utc) + timedelta(days=days_from_now, hours=hour - datetime.now(timezone.utc).hour)

events_data = [
    # ── Movies ────────────────────────────────────────────────────────────────
    dict(name="Avengers: Doomsday — Opening Night",
         description="Marvel's most anticipated blockbuster. Earth's mightiest heroes face their greatest threat yet. IMAX experience available.",
         event_time=dt(7),  event_type=EventType.movie,
         venue=venues["PVR Cinemas — Hall 1"]),

    dict(name="Stree 3 — Premiere Show",
         description="The horror-comedy franchise is back! Rajkummar Rao and Shraddha Kapoor return in this hilarious sequel set in Chanderi.",
         event_time=dt(10), event_type=EventType.movie,
         venue=venues["INOX Multiplex — Screen 3"]),

    dict(name="Interstellar — 10th Anniversary IMAX Re-release",
         description="Christopher Nolan's space epic returns to IMAX screens with restored 4K visuals and Dolby Atmos sound.",
         event_time=dt(14), event_type=EventType.movie,
         venue=venues["PVR Cinemas — Hall 1"]),

    dict(name="Pushpa 3 — The Rise Continues",
         description="Allu Arjun is back as Pushpa Raj in the blockbuster sequel. Witness the phenomenon on the biggest screen.",
         event_time=dt(21), event_type=EventType.movie,
         venue=venues["INOX Multiplex — Screen 3"]),

    # ── Concerts ──────────────────────────────────────────────────────────────
    dict(name="Arijit Singh Live — Dil Se",
         description="An intimate evening with India's most-loved playback singer. Expect soulful renditions of Tum Hi Ho, Channa Mereya, and more.",
         event_time=dt(15), event_type=EventType.concert,
         venue=venues["Jio World Garden — Mumbai"]),

    dict(name="Dua Lipa — Future Nostalgia World Tour",
         description="Pop superstar Dua Lipa brings her record-breaking world tour to India for one night only. Dance-pop at its finest.",
         event_time=dt(30), event_type=EventType.concert,
         venue=venues["Nehru Stadium — Delhi"]),

    dict(name="AP Dhillon — Brown Munde India Tour",
         description="Punjabi sensation AP Dhillon brings his signature blend of R&B and Punjabi pop to Mumbai. Tere Te, With You, and more.",
         event_time=dt(18), event_type=EventType.concert,
         venue=venues["NSCI Dome — Mumbai"]),

    dict(name="Coldplay — Music of the Spheres Tour",
         description="One of the biggest bands in the world returns! Chris Martin and Coldplay bring their iconic light show to London.",
         event_time=dt(45), event_type=EventType.concert,
         venue=venues["The O2 Arena — London"]),

    dict(name="Shreya Ghoshal — Unplugged",
         description="An intimate acoustic evening with the nightingale of Bollywood. Experience her golden voice like never before — up close and personal.",
         event_time=dt(25), event_type=EventType.concert,
         venue=venues["Phoenix Marketcity — Pune"]),

    dict(name="Kendrick Lamar — GNX Tour",
         description="Pulitzer Prize winner and rap legend Kendrick Lamar performs his critically acclaimed album live. Not To Be Missed.",
         event_time=dt(60), event_type=EventType.concert,
         venue=venues["Madison Square Garden — NYC"]),

    # ── Comedy Shows ──────────────────────────────────────────────────────────
    dict(name="Zakir Khan — Kaksha Gyarvi Live",
         description="'Sakht Launda' Zakir Khan brings his new stand-up special to Pune. A night of relatable desi humour you can't miss.",
         event_time=dt(12), event_type=EventType.meetup,
         venue=venues["Phoenix Marketcity — Pune"]),

    dict(name="Kenny Sebastian — Don't Be That Person",
         description="Kenny Sebastian's brand new stand-up show tackles millennial angst, awkward family dinners, and everything in between.",
         event_time=dt(20), event_type=EventType.meetup,
         venue=venues["NSCI Dome — Mumbai"]),

    dict(name="Trevor Noah — Off the Record (Mumbai)",
         description="Former Daily Show host Trevor Noah brings his world tour to India. Sharp wit, global politics, and laugh-out-loud comedy.",
         event_time=dt(35), event_type=EventType.meetup,
         venue=venues["Jio World Garden — Mumbai"]),

    # ── Tech Events ───────────────────────────────────────────────────────────
    dict(name="Google I/O Extended — Delhi 2026",
         description="The biggest Google I/O watch party in India. Live streams, hands-on demos with Gemini AI, talks by Google Developer Experts.",
         event_time=dt(8),  event_type=EventType.meetup,
         venue=venues["Nehru Stadium — Delhi"]),

    dict(name="PyCon India 2026",
         description="India's premier Python conference. Two days of talks on AI/ML, web development, data science, and open-source. Workshops included.",
         event_time=dt(40), event_type=EventType.meetup,
         venue=venues["Jio World Garden — Mumbai"]),
]

print("\nCreating events...")
for e in events_data:
    existing_event = db.query(Event).filter_by(name=e["name"]).first()
    if existing_event:
        print(f"  SKIP (exists): {e['name']}")
        continue
    ev = Event(
        name=e["name"],
        description=e["description"],
        event_time=e["event_time"],
        event_type=e["event_type"],
        venue_id=e["venue"].id,
        organizer_id=organizer.id,
    )
    db.add(ev)
    print(f"  Created: [{e['event_type'].value.upper():8s}] {e['name']}")

db.commit()
db.close()
print("\n✅ Seed complete!")
print(f"\nOrganizer login:")
print(f"  Email:    organizer@bookingapp.dev")
print(f"  Password: Organizer@123")
