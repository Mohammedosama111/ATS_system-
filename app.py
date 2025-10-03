import os
import streamlit as st
from dotenv import load_dotenv
from database.db_manager import init_db, SessionLocal
from database.models import Base, Resume, Job, Decision
from utils.resume_parser import parse_resume_file
from llm.llm_handler import get_reviewer_chain, review_resumes

load_dotenv()

st.set_page_config(page_title="ATS Agent", layout="wide")

# Initialize DB
engine, _Session = init_db()
Base.metadata.create_all(bind=engine)

st.title("ATS Agent: Resume Screening")

with st.sidebar:
    st.header("Settings")
    provider = st.selectbox("LLM Provider", ["openai", "anthropic", "google"], index=["openai","anthropic","google"].index(os.getenv("DEFAULT_LLM_PROVIDER", "openai")))
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Job Description")
    job_title = st.text_input("Job Title", "Software Engineer")
    job_desc = st.text_area("Job Description", height=220, placeholder="Paste the JD here...")
    hr_prompt = st.text_area("Extra HR Instructions", height=120, placeholder="Any specific requirements or preferences...")

with col2:
    st.subheader("Resumes Upload")
    uploads = st.file_uploader("Upload resumes (PDF/DOCX)", type=["pdf","docx"], accept_multiple_files=True)
    start = st.button("Run Screening")

if start:
    if not job_desc or not uploads:
        st.warning("Please provide a job description and at least one resume.")
        st.stop()

    with st.spinner("Parsing resumes and running LLM review..."):
        session = _Session()
        try:
            # Save Job
            job = Job(title=job_title, description=job_desc, hr_prompt=hr_prompt)
            session.add(job)
            session.commit()
            session.refresh(job)

            parsed_resumes = []
            id_to_name = {}
            for file in uploads:
                text = parse_resume_file(file)
                resume = Resume(filename=file.name, content=text)
                session.add(resume)
                session.commit()
                session.refresh(resume)
                parsed_resumes.append((resume, text))
                id_to_name[resume.id] = resume.filename

            chain = get_reviewer_chain(provider=provider, temperature=temperature)
            results = review_resumes(chain, job_desc, hr_prompt, [(r.id, t) for r, t in parsed_resumes])

            approved, rejected = [], []
            for (resume_id, decision, rationale) in results:
                dec = Decision(job_id=job.id, resume_id=resume_id, decision=decision, rationale=rationale)
                session.add(dec)
                if decision == "approved":
                    approved.append((resume_id, rationale))
                else:
                    rejected.append((resume_id, rationale))
            session.commit()
        finally:
            session.close()

    st.success("Screening complete")

    st.subheader("Approved Resumes")
    for rid, why in approved:
        name = id_to_name.get(rid, f"Resume ID {rid}")
        st.markdown(f"- {name} (ID {rid}): {why}")

    st.subheader("Rejected Resumes")
    for rid, why in rejected:
        name = id_to_name.get(rid, f"Resume ID {rid}")
        st.markdown(f"- {name} (ID {rid}): {why}")

    with st.expander("Raw decisions"):
        st.json([
            { "resume_id": rid, "resume_name": id_to_name.get(rid), "decision": "approved", "rationale": why }
            for rid, why in approved
        ] + [
            { "resume_id": rid, "resume_name": id_to_name.get(rid), "decision": "rejected", "rationale": why }
            for rid, why in rejected
        ])
