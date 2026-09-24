// Gym Membership Management System: Review 2 live demo queries for mongosh / Compass shell.
// Run AFTER `python demo.py --section setup` has created and seeded gym_db.
//   mongosh "mongodb://localhost:27017/?directConnection=true" mongosh/demo_queries.js
// or paste blocks one at a time during the review.

db = db.getSiblingDB("gym_db");
const show = (label, x) => { print("\n--- " + label); printjson(x); };

// ---------- Counts (minimum 50 records requirement)
show("Document counts", db.getCollectionNames().sort().map(c => ({ [c]: db[c].countDocuments() })));

// ---------- CREATE
db.members.deleteOne({ member_id: "MEM2001" });
db.members.insertOne({
  member_id: "MEM2001", name: "Demo Member", email: "demo.member@example.com", phone: "9000012345",
  dob: ISODate("2003-06-01"), gender: "Female", password_hash: "$2b$12$placeholderplaceholderplace",
  role: "member",
  membership: { type: "Basic", status: "active", start_date: ISODate("2026-09-01"), end_date: ISODate("2027-08-31") },
  assigned_trainer_id: db.trainers.findOne({ trainer_id: "TRN03" })._id, referred_by: null,
  address: { line1: "VIT Campus", city: "Vellore", pincode: "632014" },
  emergency_contact: { name: "Parent", phone: "9000054321" }, created_at: new Date()
});

// Validator rejects bad data (tier "Gold" is not allowed)
try {
  db.members.insertOne({ member_id: "MEM2002", name: "Bad", email: "bad@x.com", password_hash: "x", role: "member",
    membership: { type: "Gold", status: "active", start_date: new Date(), end_date: new Date() } });
} catch (e) { print("\nValidator rejected document: " + e.message); }

// ---------- READ
show("READ member (password hidden)", db.members.findOne({ member_id: "MEM2001" }, { password_hash: 0 }));
show("READ active VIP members in Chennai",
  db.members.find({ "membership.type": "VIP", "membership.status": "active", "address.city": "Chennai" },
                  { _id: 0, member_id: 1, name: 1 }).toArray());
show("READ Yoga trainers (array field)", db.trainers.find({ specialization: "Yoga" }, { _id: 0, trainer_id: 1, name: 1 }).toArray());

// ---------- UPDATE
db.members.updateOne({ member_id: "MEM2001" }, { $set: { "membership.type": "Premium" } });
db.trainers.updateOne({ trainer_id: "TRN03" }, { $addToSet: { specialization: "Meditation" } });
// atomic enrollment with capacity guard in the filter
const me = db.members.findOne({ member_id: "MEM2001" });
const r = db.classes.updateOne(
  { class_id: "CLS01", "enrolled_members.member_id": { $ne: me._id },
    $expr: { $lt: [{ $size: "$enrolled_members" }, "$capacity"] } },
  { $push: { enrolled_members: { member_id: me._id, member_name: me.name, enrolled_on: new Date() } } });
show("UPDATE enroll in CLS01", r);
show("UPDATE overdue sweep", db.payments.updateMany(
  { status: "pending", due_date: { $lt: ISODate("2026-09-24") } }, { $set: { status: "overdue" } }));

// ---------- DELETE
db.classes.updateOne({ class_id: "CLS01" }, { $pull: { enrolled_members: { member_id: me._id } } });
show("DELETE demo member", db.members.deleteOne({ member_id: "MEM2001" }));

// ---------- AGGREGATION: monthly revenue by tier
show("AGG revenue trend", db.payments.aggregate([
  { $match: { status: "paid" } },
  { $lookup: { from: "members", localField: "member_id", foreignField: "_id", as: "m" } },
  { $unwind: "$m" },
  { $group: { _id: { month: { $dateToString: { format: "%Y-%m", date: "$billing_period_start" } }, tier: "$m.membership.type" },
              revenue: { $sum: "$amount" } } },
  { $sort: { "_id.month": 1, "_id.tier": 1 } }
]).toArray());

// ---------- AGGREGATION: class popularity
show("AGG class popularity", db.attendance.aggregate([
  { $group: { _id: "$class_id", marked: { $sum: 1 },
              attended: { $sum: { $cond: [{ $in: ["$status", ["present", "late"]] }, 1, 0] } } } },
  { $lookup: { from: "classes", localField: "_id", foreignField: "_id", as: "c" } },
  { $unwind: "$c" },
  { $project: { _id: 0, class: "$c.class_name",
                rate_pct: { $round: [{ $multiply: [{ $divide: ["$attended", "$marked"] }, 100] }, 1] } } },
  { $sort: { rate_pct: -1 } }
]).toArray());

// ---------- AGGREGATION: $facet + $bucket dashboard
show("AGG membership overview", db.members.aggregate([
  { $addFields: { age: { $dateDiff: { startDate: "$dob", endDate: ISODate("2026-09-24"), unit: "year" } } } },
  { $facet: {
      by_tier: [{ $group: { _id: "$membership.type", n: { $sum: 1 } } }],
      age_groups: [{ $bucket: { groupBy: "$age", boundaries: [18, 25, 35, 45, 60], default: "60+", output: { n: { $sum: 1 } } } }]
  } }
]).toArray());

// ---------- GRAPH TRAVERSAL: referral network
show("GRAPH top referral networks", db.members.aggregate([
  { $match: { referred_by: null } },
  { $graphLookup: { from: "members", startWith: "$_id", connectFromField: "_id",
                    connectToField: "referred_by", as: "net", depthField: "level" } },
  { $project: { _id: 0, member_id: 1, name: 1, size: { $size: "$net" }, levels: { $add: [{ $max: "$net.level" }, 1] } } },
  { $match: { size: { $gt: 0 } } }, { $sort: { size: -1 } }, { $limit: 5 }
]).toArray());

// ---------- INDEXING: compare plans
const mid = db.members.findOne({ member_id: "MEM1001" })._id;
const scan = db.attendance.find({ member_id: mid }).sort({ date: -1 }).hint({ $natural: 1 }).explain("executionStats").executionStats;
const ixs  = db.attendance.find({ member_id: mid }).sort({ date: -1 }).hint("ix_member_date").explain("executionStats").executionStats;
show("INDEX collection scan vs index scan", {
  collscan: { docsExamined: scan.totalDocsExamined, returned: scan.nReturned },
  ixscan:   { docsExamined: ixs.totalDocsExamined, keysExamined: ixs.totalKeysExamined, returned: ixs.nReturned } });

// ---------- TRANSACTION: renew membership atomically (needs replica set)
const s = db.getMongo().startSession();
try {
  s.startTransaction({ readConcern: { level: "snapshot" }, writeConcern: { w: "majority" } });
  const sdb = s.getDatabase("gym_db");
  const m = sdb.members.findOne({ member_id: "MEM1012" });
  sdb.payments.insertOne({ payment_id: "PAY9999", member_id: m._id, member_name: m.name, amount: 4500,
    currency: "INR", payment_mode: "UPI", status: "paid", billing_period_start: new Date(),
    billing_period_end: new Date(), payment_date: new Date(), due_date: new Date() });
  sdb.members.updateOne({ _id: m._id }, { $set: { "membership.status": "active" } });
  s.abortTransaction();   // demo: roll back; use s.commitTransaction() to keep the changes
  show("TXN aborted; PAY9999 exists?", db.payments.countDocuments({ payment_id: "PAY9999" }));
} finally { s.endSession(); }
