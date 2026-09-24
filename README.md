# Gym Membership Management System (MongoDB)

Database Systems Project, Review 2: Database Implementation and Core Functionalities
Liz Alex (24BCE2978), Malika Balaji (24BAI0114), Nehaa Prabhu (24BAI0130). Submitted to Prof. Lydia Jane G.

## 1. What is in this repository

| Path | Purpose | Rubric item |
|---|---|---|
| `gym_db/schema.py` | Creates the 7 collections with `$jsonSchema` validators | Implementation |
| `gym_db/seed.py` | Loads 1,016 reproducible sample documents | Implementation |
| `gym_db/indexes.py` | 19 indexes (unique, compound, multikey, text, partial) and `explain()` comparison | Advanced |
| `gym_db/crud.py` | Create, read, update, delete for every collection, with referential-integrity rules | CRUD |
| `gym_db/aggregations.py` | 8 aggregation pipelines, 2 `$graphLookup` traversals, 1 view | Advanced |
| `gym_db/transactions.py` | 2 multi-document ACID transactions with rollback | Advanced |
| `demo.py` | Runs the full intermediate demonstration in rubric order | Demo |
| `mongosh/demo_queries.js` | Same highlights as raw shell queries for the live viva | Demo |
| `data/*.json` | Exported dataset (Extended JSON) for `mongoimport` | Sample data |
| `tests/test_gym_db.py` | 6 automated tests (offline) | Quality |

## 2. Setup

```bash
pip install -r requirements.txt
```

Transactions need a replica set. Any ONE of these works:

```bash
# A. Docker (simplest)
docker run -d --name gymdb -p 27017:27017 mongo:8 --replSet rs0
docker exec gymdb mongosh --eval "rs.initiate()"

# B. Local mongod
mongod --dbpath ./db --replSet rs0          # new terminal
mongosh --eval "rs.initiate()"

# C. MongoDB Atlas free cluster (already a replica set)
export MONGO_URI="mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/"
```

A plain standalone `mongod` also works; the demo simply skips the transaction section.

## 3. Run

```bash
python demo.py                  # full demo on the live database (recreates gym_db)
python demo.py --section agg    # setup + one section: crud | agg | graph | index | txn
python demo.py --mock           # no server needed (in-memory mongomock)
python -m pytest -q             # automated tests
mongosh "mongodb://localhost:27017/?directConnection=true" mongosh/demo_queries.js
```

`demo.py` drops and recreates `gym_db` every run, so the demonstration always starts from the same state.
All dates are relative to a fixed reference date of 24 Sep 2026 (`gym_db/config.py`) so reports are reproducible.

## 4. Sample data

| Collection | Documents | Notes |
|---|---:|---|
| trainers | 8 | specialization and availability embedded |
| members | 60 | 24 Basic, 22 Premium, 14 VIP; 50 active, 6 expired, 4 frozen; referral links |
| workout_plans | 76 | 60 active plus 16 completed; 3 to 4 embedded exercises each |
| classes | 8 | weekly schedule and bounded roster embedded |
| class_sessions | 64 | 4 weeks, 7 Sep to 4 Oct 2026 |
| attendance | 580 | present, late, absent per completed session |
| payments | 220 | Jul to Oct 2026; paid, pending and overdue |
| **Total** | **1,016** | |

Login for testing: trainers `priya.menon@gym.com` / `Trainer@01` (pattern `Trainer@NN`), members use `Member@<member number>`, e.g. `Member@1001`.

## 5. Change from Review 1

One field was added to `members`: `referred_by` (ObjectId of the referring member, or null). It models the gym's referral
programme as a self-referencing graph, so the `$graphLookup` traversal has a real business use.

## 6. Pushing to GitHub

```bash
git remote add origin https://github.com/<team-account>/gym-membership-db.git
git push -u origin main
```
