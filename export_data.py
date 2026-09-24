"""Export the seeded dataset to data/*.json (MongoDB Extended JSON) for mongoimport or review.

    python export_data.py            # from the live database
    python export_data.py --mock     # generate + export without a server
    mongoimport --db gym_db --collection members --jsonArray --file data/members.json
"""
import argparse
import os

from bson import json_util

from gym_db.config import COLLECTIONS, get_db, is_mock
from gym_db.schema import create_collections
from gym_db.seed import seed

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true")
    db = get_db(mock=ap.parse_args().mock)
    if is_mock():
        create_collections(db)
        seed(db)
    os.makedirs("data", exist_ok=True)
    for c in COLLECTIONS:
        docs = list(db[c].find())
        with open(f"data/{c}.json", "w") as f:
            f.write(json_util.dumps(docs, indent=2, json_options=json_util.RELAXED_JSON_OPTIONS))
        print(f"data/{c}.json  {len(docs)} documents")
