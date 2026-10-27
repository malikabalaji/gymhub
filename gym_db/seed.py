"""Step 2: load a realistic, reproducible sample dataset.

Volumes (well above the 50-record minimum):
  trainers 8 | members 60 | workout_plans 75 | classes 8
  class_sessions 64 | attendance ~600 | payments ~200
Random choices use a fixed seed, so every run produces identical data.
"""
import random
from datetime import datetime, timedelta

import bcrypt
from bson import ObjectId

from .config import REFERENCE_DATE, TIER_FEES

rng = random.Random(2026)
# Cheap work factor for bulk seeding; the application uses the default (12) for real sign-ups.
_SALT = bcrypt.gensalt(rounds=4)


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), _SALT).decode()


FIRST_M = ["Arjun", "Rahul", "Karthik", "Vikram", "Siddharth", "Aditya", "Rohan", "Nikhil",
           "Pranav", "Harish", "Gautham", "Varun", "Manoj", "Ashwin", "Dev"]
FIRST_F = ["Ananya", "Divya", "Kavya", "Meera", "Sneha", "Pooja", "Lakshmi", "Nandini",
           "Aishwarya", "Ritika", "Swathi", "Keerthana", "Shreya", "Isha", "Tara"]
LAST = ["Rao", "Iyer", "Nair", "Menon", "Reddy", "Sharma", "Krishnan", "Pillai",
        "Kumar", "Shetty", "Das", "Varma", "Joshi", "Bhat", "Subramanian"]
CITIES = [("Vellore", "632014"), ("Katpadi", "632007"), ("Chennai", "600040"),
          ("Hosur", "635109"), ("Bengaluru", "560034")]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

TRAINERS = [
    ("Priya Menon", ["Strength Training", "CrossFit"], "ACE-CPT", 6),
    ("Rohit Sharma", ["HIIT", "Functional Training"], "NASM-CPT", 4),
    ("Deepa Krishnan", ["Yoga", "Pilates"], "RYT-500", 9),
    ("Sanjay Pillai", ["Bodybuilding", "Strength Training"], "ISSA-CPT", 11),
    ("Meenakshi Iyer", ["Zumba", "Aerobics"], "ZIN Licensed", 5),
    ("Farhan Ali", ["Spin", "Cardio"], "ACSM-EP", 3),
    ("Kavitha Reddy", ["Yoga", "Mobility"], "RYT-200", 7),
    ("Vivek Nair", ["CrossFit", "Olympic Lifting"], "CF-L2", 8),
]

CLASSES = [  # name, category, trainer index, capacity, [(day, start, end, room)]
    ("Morning Yoga", "Yoga", 2, 20, [("Mon", "07:00", "08:00", "A1"), ("Thu", "07:00", "08:00", "A1")]),
    ("Power Zumba", "Zumba", 4, 25, [("Tue", "18:00", "19:00", "B1"), ("Fri", "18:00", "19:00", "B1")]),
    ("CrossFit Burn", "CrossFit", 7, 15, [("Mon", "18:30", "19:30", "C1"), ("Wed", "18:30", "19:30", "C1")]),
    ("HIIT Express", "HIIT", 1, 18, [("Tue", "06:30", "07:15", "B2"), ("Sat", "08:00", "08:45", "B2")]),
    ("Spin Cycle", "Cardio", 5, 16, [("Wed", "07:00", "07:45", "S1"), ("Sat", "09:00", "09:45", "S1")]),
    ("Pilates Core", "Pilates", 2, 12, [("Tue", "10:00", "11:00", "A2"), ("Thu", "10:00", "11:00", "A2")]),
    ("Strength 101", "Strength", 3, 14, [("Mon", "17:00", "18:00", "G1"), ("Fri", "17:00", "18:00", "G1")]),
    ("Evening Yoga", "Yoga", 6, 20, [("Wed", "19:00", "20:00", "A1"), ("Sat", "17:00", "18:00", "A1")]),
]

GOALS = {
    "Muscle Gain": [("Bench Press", 40), ("Deadlift", 60), ("Squat", 50), ("Overhead Press", 25),
                    ("Barbell Row", 35), ("Bicep Curl", 10)],
    "Weight Loss": [("Kettlebell Swing", 12), ("Burpees", 0), ("Treadmill Intervals", 0),
                    ("Jump Squats", 0), ("Rowing Machine", 0), ("Mountain Climbers", 0)],
    "Endurance": [("Cycling", 0), ("Rowing Machine", 0), ("Lunges", 8), ("Plank", 0),
                  ("Box Jumps", 0), ("Treadmill Intervals", 0)],
    "Flexibility": [("Sun Salutation", 0), ("Hamstring Stretch", 0), ("Hip Opener Flow", 0),
                    ("Plank", 0), ("Cat-Cow Stretch", 0)],
    "Strength": [("Deadlift", 80), ("Squat", 70), ("Bench Press", 55), ("Pull Ups", 0),
                 ("Farmer Walk", 24)],
}
DAY_INDEX = {d: i for i, d in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])}


def _trainers():
    docs = []
    for i, (name, spec, cert, yrs) in enumerate(TRAINERS, start=1):
        first = name.split()[0].lower()
        docs.append({
            "_id": ObjectId(),
            "trainer_id": f"TRN{i:02d}",
            "name": name,
            "email": f"{first}.{name.split()[1].lower()}@gym.com",
            "phone": f"98450{12340 + i:05d}",
            "password_hash": _hash(f"Trainer@{i:02d}"),
            "role": "trainer",
            "specialization": spec,
            "certification": cert,
            "experience_years": yrs,
            "availability": [{"day": d, "start_time": "06:00" if i % 2 else "12:00",
                              "end_time": "14:00" if i % 2 else "21:00"}
                             for d in rng.sample(DAYS, 4)],
            "created_at": datetime(2024, 1, 1) + timedelta(days=30 * i),
        })
    return docs


def _members(trainers):
    docs, used = [], set()
    # Target mix: 24 Basic, 22 Premium, 14 VIP; 50 active, 6 expired, 4 frozen
    tiers = ["Basic"] * 24 + ["Premium"] * 22 + ["VIP"] * 14
    statuses = ["active"] * 50 + ["expired"] * 6 + ["frozen"] * 4
    rng.shuffle(tiers)
    rng.shuffle(statuses)
    for i in range(60):
        gender = "Male" if i % 2 == 0 else "Female"
        while True:
            first = rng.choice(FIRST_M if gender == "Male" else FIRST_F)
            last = rng.choice(LAST)
            if (first, last) not in used:
                used.add((first, last))
                break
        start = datetime(2026, rng.randint(1, 6), 1)
        status = statuses[i]
        end = datetime(2026, 8, 31) if status == "expired" else datetime(start.year + 1, start.month, 1) - timedelta(days=1)
        city, pin = rng.choice(CITIES)
        docs.append({
            "_id": ObjectId(),
            "member_id": f"MEM{1001 + i}",
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}{i + 1}@example.com",
            "phone": f"9{rng.randint(100000000, 999999999)}",
            "dob": datetime(rng.randint(1975, 2006), rng.randint(1, 12), rng.randint(1, 28)),
            "gender": gender,
            "password_hash": _hash(f"Member@{1001 + i}"),
            "role": "member",
            "membership": {"type": tiers[i], "status": status, "start_date": start, "end_date": end},
            "assigned_trainer_id": rng.choice(trainers)["_id"],
            "referred_by": None,
            "address": {"line1": f"{rng.randint(1, 250)} {rng.choice(['MG Road', 'Gandhi Nagar', 'Anna Salai', 'Brigade Road', 'Katpadi Main Road'])}",
                        "city": city, "pincode": pin},
            "emergency_contact": {"name": f"{rng.choice(FIRST_F + FIRST_M)} {last}",
                                  "phone": f"9{rng.randint(100000000, 999999999)}"},
            "created_at": start - timedelta(days=rng.randint(1, 15)),
        })
    # Referral network (used by the $graphLookup demo): some members were referred by earlier members
    # Referrers are usually recent joiners, which produces multi-level chains.
    for i in range(4, 60):
        if rng.random() < 0.55:
            docs[i]["referred_by"] = docs[rng.randint(max(0, i - 6), i - 1)]["_id"]
    return docs


def _workout_plans(members, trainers):
    tmap = {t["_id"]: t for t in trainers}
    docs, n = [], 5001
    for m in members:
        plans = [("active", m["membership"]["start_date"])]
        if rng.random() < 0.25:  # some members also have an earlier completed plan
            plans.insert(0, ("completed", m["membership"]["start_date"] - timedelta(days=70)))
        for status, created in plans:
            goal = rng.choice(list(GOALS))
            picks = rng.sample(GOALS[goal], k=min(4, len(GOALS[goal])))
            days = sorted(rng.sample(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], k=len(picks)), key=DAY_INDEX.get)
            t = tmap[m["assigned_trainer_id"]]
            docs.append({
                "_id": ObjectId(),
                "plan_id": f"WP{n}",
                "member_id": m["_id"], "member_name": m["name"],
                "trainer_id": t["_id"], "trainer_name": t["name"],
                "goal": goal,
                "duration_weeks": rng.choice([6, 8, 10, 12]),
                "status": status,
                "exercises": [{"day": d, "exercise_name": ex, "sets": rng.choice([3, 4, 5]),
                               "reps": rng.choice([8, 10, 12, 15]),
                               "weight_kg": w + rng.choice([0, 5, 10]) if w else 0,
                               "notes": ""} for d, (ex, w) in zip(days, picks)],
                "created_at": created, "updated_at": created,
            })
            n += 1
    return docs


def _classes(trainers, members):
    active = [m for m in members if m["membership"]["status"] == "active"]
    docs = []
    for i, (name, cat, t_idx, cap, sched) in enumerate(CLASSES, start=1):
        t = trainers[t_idx]
        fill = rng.randint(int(cap * 0.55), cap)  # Morning Yoga ends up busier than Pilates, etc.
        enrolled = rng.sample(active, k=min(fill, len(active)))
        docs.append({
            "_id": ObjectId(),
            "class_id": f"CLS{i:02d}", "class_name": name, "category": cat,
            "trainer_id": t["_id"], "trainer_name": t["name"], "capacity": cap,
            "schedule": [{"day_of_week": d, "start_time": s, "end_time": e, "room": r} for d, s, e, r in sched],
            "enrolled_members": [{"member_id": m["_id"], "member_name": m["name"],
                                  "enrolled_on": datetime(2026, 7, rng.randint(1, 28))} for m in enrolled],
        })
    return docs


def _sessions(classes):
    """One dated session per schedule slot for 4 weeks: 7 Sep to 3 Oct 2026."""
    docs, n = [], 9001
    week0 = datetime(2026, 9, 7)  # a Monday
    for c in classes:
        for w in range(4):
            for slot in c["schedule"]:
                date = week0 + timedelta(days=7 * w + DAY_INDEX[slot["day_of_week"]])
                if date < REFERENCE_DATE:
                    status = "cancelled" if rng.random() < 0.06 else "completed"
                else:
                    status = "scheduled"
                docs.append({
                    "_id": ObjectId(), "session_id": f"SES{n}",
                    "class_id": c["_id"], "class_name": c["class_name"], "trainer_id": c["trainer_id"],
                    "date": date, "start_time": slot["start_time"], "end_time": slot["end_time"],
                    "status": status,
                })
                n += 1
    return docs


def _attendance(sessions, classes):
    cmap = {c["_id"]: c for c in classes}
    reliability = {}  # each member gets a personal attendance tendency
    docs = []
    for s in sessions:
        if s["status"] != "completed":
            continue
        h, mi = map(int, s["start_time"].split(":"))
        for e in cmap[s["class_id"]]["enrolled_members"]:
            p = reliability.setdefault(e["member_id"], rng.uniform(0.45, 0.97))
            r = rng.random()
            if r < p:
                status, offset = "present", rng.randint(-10, 2)
            elif r < p + 0.08:
                status, offset = "late", rng.randint(5, 15)
            else:
                status, offset = "absent", None
            check_in = None
            if offset is not None:
                t = s["date"].replace(hour=h, minute=mi) + timedelta(minutes=offset)
                check_in = t.strftime("%H:%M")
            docs.append({
                "_id": ObjectId(), "session_id": s["_id"], "class_id": s["class_id"],
                "member_id": e["member_id"], "member_name": e["member_name"],
                "date": s["date"], "status": status, "check_in_time": check_in,
            })
    return docs


def _payments(members):
    docs, n = [], 7001
    months = [datetime(2026, 7, 1), datetime(2026, 8, 1), datetime(2026, 9, 1), datetime(2026, 10, 1)]
    for m in members:
        fee = TIER_FEES[m["membership"]["type"]]
        for start in months:
            ms = m["membership"]
            if start < ms["start_date"].replace(day=1) or start > ms["end_date"]:
                continue
            if ms["status"] == "frozen" and start >= datetime(2026, 9, 1):
                continue
            end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            due = start.replace(day=5)
            if due > REFERENCE_DATE:
                status, paid_on, mode = "pending", None, None
            elif start.month == 9 and rng.random() < 0.18:
                status, paid_on, mode = "pending", None, None  # past due; the overdue sweep will flag it
            elif start.month == 8 and rng.random() < 0.05:
                status, paid_on, mode = "overdue", None, None
            else:
                status = "paid"
                paid_on = due - timedelta(days=rng.randint(-3, 4))
                mode = rng.choices(["UPI", "card", "cash"], weights=[6, 3, 1])[0]
            docs.append({
                "_id": ObjectId(), "payment_id": f"PAY{n}",
                "member_id": m["_id"], "member_name": m["name"],
                "amount": fee, "currency": "INR", "payment_mode": mode, "status": status,
                "billing_period_start": start, "billing_period_end": end,
                "payment_date": paid_on, "due_date": due,
            })
            n += 1
    return docs


def seed(db):
    trainers = _trainers()
    members = _members(trainers)
    plans = _workout_plans(members, trainers)
    classes = _classes(trainers, members)
    sessions = _sessions(classes)
    attendance = _attendance(sessions, classes)
    payments = _payments(members)
    data = {"trainers": trainers, "members": members, "workout_plans": plans, "classes": classes,
            "class_sessions": sessions, "attendance": attendance, "payments": payments}
    for name, docs in data.items():
        db[name].insert_many(docs)
    return {k: len(v) for k, v in data.items()}
