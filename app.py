import streamlit as st
import subprocess
from pymongo import MongoClient
from src.job_api import MerojobScraper
from src.recommender import recommend_jobs

# ------------------ PAGE CONFIG ------------------
st.set_page_config(
    page_title="Job Intelligence Platform",
    layout="wide"
)

# ------------------ CUSTOM CSS ------------------
st.markdown(
    """
    <style>
    .job-card {
        padding: 1.2rem;
        border-radius: 12px;
        background: #0f172a;
        margin-bottom: 1.2rem;
        border: 1px solid #1e293b;
    }
    .job-meta {
        color: #94a3b8;
        font-size: 0.9rem;
    }
    .skill-chip {
        display: inline-block;
        background: #1e293b;
        padding: 0.25rem 0.6rem;
        border-radius: 8px;
        margin: 0.2rem;
        font-size: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("🔍 Job Intelligence Platform")
st.caption("Scrape, search, and get personalized job recommendations from Merojob")

# ------------------ DB CONNECTION ------------------
@st.cache_resource
def get_db():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["job_recommender"]
    return db["jobs"]

jobs_col = get_db()

# ------------------ TABS ------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "🕷️ Scrape Jobs",
    "📂 Search Database",
    "🤖 Job Recommendations",
    "📝 Self Assessment"
])

# ==================================================
# TAB 1: SCRAPE JOBS FROM MEROJOB
# ==================================================
with tab1:
    st.header("🕷️ Scrape Jobs from Merojob")
    st.caption("Fetch the latest jobs and store them in your database")

    col1, col2 = st.columns([3, 1])

    with col1:
        keyword = st.text_input(
            "Job keyword",
            placeholder="e.g. Python Developer, Backend, QA"
        )

    with col2:
        max_jobs = st.slider("Max jobs", 5, 50, 20)

    if st.button("🚀 Start Scraping", use_container_width=True):
        if not keyword:
            st.warning("Please enter a keyword.")
        else:
            with st.spinner("Scraping jobs from Merojob..."):
                scraper = MerojobScraper(max_jobs=max_jobs)
                jobs = scraper.scrape(keyword)

                inserted = 0
                for job in jobs:
                    if not jobs_col.find_one({"url": job.get("url")}):
                        jobs_col.insert_one(job)
                        inserted += 1

            st.success(f"✅ {inserted} new jobs saved to database.")

# ==================================================
# TAB 2: SEARCH JOBS FROM DATABASE
# ==================================================
with tab2:
    st.header("📂 Search Jobs")
    st.caption("Explore all scraped jobs stored in your database")

    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "Search",
            placeholder="Title, skills, company, description"
        )

    with col2:
        limit = st.selectbox("Results", [10, 20, 50, 100], index=1)

    query = {}
    if search_query:
        query = {
            "$or": [
                {"title": {"$regex": search_query, "$options": "i"}},
                {"company": {"$regex": search_query, "$options": "i"}},
                {"description": {"$regex": search_query, "$options": "i"}},
                {"skills_required": {"$regex": search_query, "$options": "i"}},
            ]
        }

    jobs = list(jobs_col.find(query).sort("_id", -1).limit(limit))

    st.markdown(f"### 📄 {len(jobs)} jobs found")

    if not jobs:
        st.info("No jobs found. Try another keyword.")
    else:
        for job in jobs:
            with st.container():
                st.markdown('<div class="job-card">', unsafe_allow_html=True)

                st.subheader(job.get("title", "No Title"))
                st.markdown(
                    f"<div class='job-meta'>🏢 {job.get('company', 'N/A')} "
                    f"| 📍 {job.get('location', 'N/A')}</div>",
                    unsafe_allow_html=True
                )

                if job.get("skills_required"):
                    st.markdown("🛠 **Skills**")
                    for s in job["skills_required"]:
                        st.markdown(
                            f"<span class='skill-chip'>{s}</span>",
                            unsafe_allow_html=True
                        )

                with st.expander("📄 Job Description"):
                    st.write(job.get("description", "No description available"))

                if job.get("url"):
                    st.markdown(f"🔗 [View Job Posting]({job['url']})")

                st.markdown("</div>", unsafe_allow_html=True)

# ==================================================
# TAB 3: JOB RECOMMENDATIONS
# ==================================================
with tab3:
    st.header("🤖 Job Recommendations")
    st.caption("Select your skills and get the best-matching jobs")

    user_skills_input = st.multiselect(
        "Your Skills",
        sorted({s for j in jobs_col.find() for s in j.get("skills_required", [])})
    )

    if st.button("🎯 Get Recommendations", use_container_width=True):
        user_skills = [skill.lower() for skill in user_skills_input]
        st.session_state["user_skills"] = user_skills

        if not user_skills:
            st.warning("Please select at least one skill.")
        else:
            recommended_jobs = recommend_jobs(user_skills, top_n=5)

            if not recommended_jobs:
                st.info("No jobs found matching your skills.")
            else:
                st.success("Top job matches for you")

                for idx, rec in enumerate(recommended_jobs, start=1):
                    job = rec["job"]
                    job_skills = [s.lower() for s in job.get("skills_required", [])]

                    matched_skills = sorted(set(job_skills) & set(user_skills))
                    skill_gaps = sorted(set(job_skills) - set(user_skills))

                    match_score = (
                        int((len(matched_skills) / len(job_skills)) * 100)
                        if job_skills else 0
                    )

                    with st.container():
                        st.markdown('<div class="job-card">', unsafe_allow_html=True)

                        st.subheader(f"{idx}. {job.get('title', 'No Title')}")
                        st.markdown(
                            f"<div class='job-meta'>🏢 {job.get('company', 'N/A')} "
                            f"| 📍 {job.get('location', 'N/A')}</div>",
                            unsafe_allow_html=True
                        )

                        st.progress(match_score / 100)
                        st.caption(f"🎯 Match Score: {match_score}%")

                        if matched_skills:
                            st.success(
                                "✅ Matched Skills: " +
                                ", ".join(s.title() for s in matched_skills)
                            )

                        if skill_gaps:
                            st.info(
                                "📌 Skill Gaps: " +
                                ", ".join(s.title() for s in skill_gaps)
                            )

                        with st.expander("📄 Job Description"):
                            st.write(job.get("description", "No description available"))

                        if job.get("url"):
                            st.markdown(f"🔗 [View Job Posting]({job['url']})")

                        st.markdown("</div>", unsafe_allow_html=True)


from src.mcq_engine import generate_mcqs

# ==================================================
# TAB 4: SELF ASSESSMENT
# ==================================================
with tab4:
    st.header("📝 Skill Self Assessment")
    st.caption("Test your skills with AI-generated MCQs")

    user_skills = st.session_state.get("user_skills", [])

    if not user_skills:
        st.info("Go to Job Recommendations tab and select skills first.")
    else:
        st.subheader("Select a skill to assess")

        selected_skill = st.radio(
            "Your Skills",
            user_skills,
            horizontal=True
        )

        if st.button("🧠 Generate MCQs"):
            with st.spinner("Generating questions using phi3:mini..."):
                mcq_data = generate_mcqs(selected_skill)
                st.session_state["mcqs"] = mcq_data
                st.session_state["answers"] = {}

        # ------------------ SHOW MCQS ------------------
        if "mcqs" in st.session_state:
            questions = st.session_state["mcqs"]["questions"]

            st.markdown("---")
            st.subheader(f"📚 MCQs on {selected_skill.title()}")

            for i, q in enumerate(questions):
                st.markdown(f"**Q{i+1}. {q['question']}**")

                choice = st.radio(
                    f"Select answer for Q{i+1}",
                    options=list(q["options"].keys()),
                    format_func=lambda x: f"{x}. {q['options'][x]}",
                    key=f"q_{i}"
                )

                st.session_state["answers"][i] = choice

            # ------------------ SUBMIT ------------------
            if st.button("✅ Submit Assessment"):
                score = 0

                for i, q in enumerate(questions):
                    if st.session_state["answers"].get(i) == q["answer"]:
                        score += 20

                st.markdown("---")
                st.subheader("📊 Result")
                st.metric("Score", f"{score} / 100")

                if score >= 60:
                    st.success("🎉 Great job! You have solid knowledge of this skill.")
                else:
                    st.warning("📉 Skill needs improvement")

                    st.markdown("### 📖 Recommended Resources")

                    rec_prompt = f"""
Suggest 2 books and 2 online courses to improve the skill "{selected_skill}".
Keep it concise.
"""

                    recs = subprocess.run(
                        ["ollama", "run", "gpt-oss:120b-cloud"],
                        input=rec_prompt,
                        text=True,
                        capture_output=True
                    )

                    st.write((recs.stdout or recs.stderr or "No recommendations generated.").strip())
