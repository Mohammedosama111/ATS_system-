import os
import streamlit as st
from dotenv import load_dotenv
from database.db_manager import init_db, SessionLocal, migrate_schema
from database.models import Base, Resume, Job, Decision
from utils.resume_parser import parse_resume_file
from llm.llm_handler import get_reviewer_chain, review_resumes

# Suppress ALTS credentials warning for local development
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '2'

load_dotenv()

st.set_page_config(page_title="ATS Agent", layout="wide")

# Initialize DB
engine, _Session = init_db()
Base.metadata.create_all(bind=engine)
# Run lightweight migration for new columns (idempotent)
migrate_schema(engine)

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

    session = _Session()
    try:
        # Save Job
        with st.spinner("Setting up job..."):
            job = Job(title=job_title, description=job_desc, hr_prompt=hr_prompt)
            session.add(job)
            session.commit()
            session.refresh(job)

        # Parse resumes
        with st.spinner(f"Parsing {len(uploads)} resume(s)..."):
            parsed_resumes = []
            id_to_name = {}
            progress_bar = st.progress(0)
            for idx, file in enumerate(uploads):
                text = parse_resume_file(file)
                resume = Resume(filename=file.name, content=text)
                session.add(resume)
                session.commit()
                session.refresh(resume)
                parsed_resumes.append((resume, text))
                id_to_name[resume.id] = resume.filename
                progress_bar.progress((idx + 1) / len(uploads))
            progress_bar.empty()

        # Run LLM review (now in parallel!)
        st.info(f"🤖 Reviewing {len(parsed_resumes)} resume(s) in parallel... This should be much faster!")
        with st.spinner("AI is analyzing resumes..."):
            chain = get_reviewer_chain(provider=provider, temperature=temperature)
            raw_results = review_resumes(chain, job_desc, hr_prompt, [(r.id, t) for r, t in parsed_resumes], provider_name=provider)
            # Normalize results shape (support older tuple version)
            results = []
            for item in raw_results:
                if isinstance(item, dict):
                    results.append(item)
                elif isinstance(item, (list, tuple)) and len(item) >= 3:
                    rid, decision, rationale = item[:3]
                    results.append({
                        "resume_id": rid,
                        "decision": decision,
                        "rationale": rationale,
                        "category": 'A' if decision == 'approved' else 'C',
                        "match_score": None,
                    })
                else:
                    continue

        # Save decisions
        with st.spinner("Saving results..."):
            categories = {"A": [], "B": [], "C": []}
            for res in results:
                try:
                    dec = Decision(
                        job_id=job.id,
                        resume_id=res["resume_id"],
                        decision=res["decision"],
                        rationale=res["rationale"],
                        category=res.get("category"),
                        match_score=res.get("match_score"),
                    )
                    session.add(dec)
                    categories.setdefault(res.get("category", "C"), []).append(res)
                except Exception as e:
                    st.error(f"Failed to save decision for resume {res.get('resume_id')}: {e}")
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                st.error(f"Database commit failed: {e}")
    finally:
        session.close()

    st.success("Screening complete")

    st.subheader("Category A (Strong Fit)")
    for res in categories.get("A", []):
        name = id_to_name.get(res["resume_id"], f"Resume ID {res['resume_id']}")
        score = res.get("match_score")
        st.markdown(f"- {name} (ID {res['resume_id']}) Score: {score if score is not None else '—'} — {res['rationale']}")

    st.subheader("Category B (Potential Fit)")
    for res in categories.get("B", []):
        name = id_to_name.get(res["resume_id"], f"Resume ID {res['resume_id']}")
        score = res.get("match_score")
        st.markdown(f"- {name} (ID {res['resume_id']}) Score: {score if score is not None else '—'} — {res['rationale']}")

    st.subheader("Category C (Not Suitable)")
    for res in categories.get("C", []):
        name = id_to_name.get(res["resume_id"], f"Resume ID {res['resume_id']}")
        score = res.get("match_score")
        st.markdown(f"- {name} (ID {res['resume_id']}) Score: {score if score is not None else '—'} — {res['rationale']}")

    with st.expander("Raw decisions JSON"):
        st.json(results)

    # Show real token usage if Google provider and usage data present
    if provider == "google":
        usage_rows = [r.get("usage") for r in results if r.get("usage")]
        if usage_rows:
            total_prompt = sum(u.get("prompt_tokens") or 0 for u in usage_rows)
            total_response = sum(u.get("response_tokens") or 0 for u in usage_rows)
            total_total = sum(u.get("total_tokens") or 0 for u in usage_rows)
            st.subheader("Token Usage (Google Gemini - aggregated)")
            st.caption(f"Prompt tokens: {total_prompt} | Response tokens: {total_response} | Total tokens: {total_total}")
            with st.expander("Per resume usage"):
                for r in results:
                    if r.get("usage"):
                        u = r["usage"]
                        st.write(f"Resume {r['resume_id']}: prompt={u.get('prompt_tokens')} response={u.get('response_tokens')} total={u.get('total_tokens')}")
        else:
            st.info("No usage metadata returned by provider.")

    # Token usage summary removed.
