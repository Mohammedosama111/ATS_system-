from langchain_core.prompts import ChatPromptTemplate

SYSTEM_PROMPT = (
    "You are an expert technical recruiter. Read the job description and a candidate resume. "
    "Provide a three-tier categorization plus approve/reject flag. "
    "Categories: A = strong/ready (>=80% match), B = partial/potential (50-79%), C = not suitable (<50%). "
    "Always estimate a numeric match_score 0-100. decision should be 'approved' if category is A, 'rejected' if C, and may be either for B depending on evidence. "
    "Keep rationale to 1-3 concise bullet-style sentences. "
    "Output strictly as JSON with keys: decision ('approved'|'rejected'), category ('A'|'B'|'C'), match_score (int), rationale (string)."
)

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "Job Description:\n{job_description}\n\nHR Instructions:\n{hr_prompt}\n\nResume (id={resume_id}):\n{resume_text}\n\nReturn JSON only with keys decision, category, match_score, rationale."),
])
