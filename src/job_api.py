import requests
from typing import List, Dict
from src.helper import extract_skills_from_description


class MerojobScraper:
    BASE_URL = "https://api.merojob.com/api/v1/jobs/"

    def __init__(self, max_jobs=20):
        self.max_jobs = max_jobs
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "application/json",
            "user-agent": "Mozilla/5.0"
        })

    def scrape(self, keyword: str) -> List[Dict]:
        jobs = []
        page = 1

        while len(jobs) < self.max_jobs:
            res = self.session.get(self.BASE_URL, params={
                "q": keyword,
                "page": page,
                "page_size": 20
            })

            if res.status_code != 200:
                break

            data = res.json().get("results", [])
            if not data:
                break

            for job in data:
                title = job.get("title")
                if not title:
                    continue

                description = f"{job.get('description','')} {job.get('specification','')}"
                skills = extract_skills_from_description(description)

                jobs.append({
                    "job_id": str(job.get("id")),
                    "title": title,
                    "company": job.get("client", {}).get("client_name"),
                    "location": job.get("location"),
                    "description": description,
                    "skills_required": skills,
                    "platform": "Merojob",
                    "url": f"https://merojob.com{job.get('absolute_url','')}",
                    "experience_level": "experience_required"
                })

                if len(jobs) >= self.max_jobs:
                    break

            page += 1

        return jobs
