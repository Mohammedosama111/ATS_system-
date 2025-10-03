from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = (
    "You are an expert technical recruiter. Read the job description and a candidate resume. "
    "Decide if the candidate should be APPROVED for interview or REJECTED. "
    "Explain briefly in 1-3 bullet points focusing on clear evidence. "
    "Output strictly as JSON with keys: decision ('approved'|'rejected'), rationale (string)."
)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Job Description:\n{job_description}\n\nHR Instructions:\n{hr_prompt}\n\nResume (id={resume_id}):\n{resume_text}\n\nReturn JSON only."),
])
