import json
from pymongo import MongoClient, ASCENDING
from src.helper import extract_skills_from_description

client = MongoClient("mongodb://localhost:27017/")
db = client["job_recommender"]
job_collection = db["jobs"]

job_collection.create_index(
    [("job_id", 1)],
    unique=True,
    partialFilterExpression={
        "job_id": {"$exists": True}
    }
)

with open("jobs.json", "r", encoding="utf-8") as f:
    jobs = json.load(f)

inserted = 0
skipped = 0

for job in jobs:
    title = job.get("title", "").strip()
    company = job.get("companyName", "").strip()
    description = job.get("description", "")

    job_id = job.get("id")
    if not job_id:
        job_id = f"json_{title.lower().replace(' ', '_')}_{company.lower().replace(' ', '_')}"

    skills = extract_skills_from_description(description)

    doc = {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": job.get("location"),
        "description": description,
        "skills_required": skills,
        "platform": "Linkedin",
        "url": job.get("jobUrl"),
        "experience_level": "experience_required"
    }

    try:
        job_collection.insert_one(doc)
        inserted += 1
    except Exception:
        skipped += 1

print(f"Inserted: {inserted}, Skipped duplicates: {skipped}")
