import json
from typing import Iterable, List, Tuple, Dict, Any
from database.db_manager import init_db, migrate_schema
from concurrent.futures import ThreadPoolExecutor, as_completed
from config.settings import settings
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from .prompts import prompt, SYSTEM_PROMPT

try:  # Optional import; only needed for direct usage metadata
    import google.generativeai as genai
except ImportError:  # pragma: no cover - environment without google lib
    genai = None  # type: ignore


def _to_json_decision(text: str) -> Tuple[str, str, str | None, int | None]:
    # Try to extract JSON from text
    try:
        data = json.loads(text)
    except Exception:
        # attempt to find a JSON substring
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                data = json.loads(text[start:end+1])
            except Exception:
                data = {"decision": "rejected", "rationale": "Invalid JSON from model"}
        else:
            data = {"decision": "rejected", "rationale": "No JSON found in model output"}

    decision = str(data.get("decision", "rejected")).lower()
    if decision not in ("approved", "rejected"):
        decision = "rejected"
    category = str(data.get("category", "")).upper()
    if category not in ("A", "B", "C"):
        # Infer category if missing using decision heuristic
        category = "A" if decision == "approved" else "C"
    # If mismatch between decision and category adjust decision to match naming policy
    if category == "A":
        decision = "approved"
    elif category == "C":
        decision = "rejected"
    match_score = data.get("match_score")
    try:
        match_score = int(match_score) if match_score is not None else None
    except Exception:
        match_score = None
    rationale = str(data.get("rationale", ""))
    return decision, rationale, category, match_score


def get_model(provider: str, temperature: float = 0.2):
    provider = provider or settings.default_llm_provider
    if provider == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        return ChatOpenAI(model="gpt-4o-mini", temperature=temperature, api_key=settings.openai_api_key)
    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        return ChatAnthropic(model="claude-3-5-sonnet-20240620", temperature=temperature, api_key=settings.anthropic_api_key)
    elif provider == "google":
        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set")
        # Use a broadly supported model to avoid v1beta 404s on some client versions
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-pro",
            api_key=settings.google_api_key,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_reviewer_chain(provider: str, temperature: float = 0.2):
    llm = get_model(provider, temperature)
    # NOTE: Using StrOutputParser means we lose provider native response metadata.
    # For Google token usage we call the native SDK separately (see below).
    chain = prompt | llm | StrOutputParser()
    return chain


def _log_usage(*_args, **_kwargs):
    # Token usage tracking removed from system.
    return None


def _google_invoke_with_usage(job_desc: str, hr_prompt: str, resume_id: int, resume_text: str) -> Tuple[str, Dict[str, int] | None]:
    """Call Gemini directly to obtain real usage metadata (prompt/response/total tokens).

    Returns tuple (text_output, usage_dict or None).
    """
    if not genai or not settings.google_api_key:
        return "", None
    try:
        genai.configure(api_key=settings.google_api_key)
        # Compose a single text prompt replicating the chat structure.
        human_section = (
            f"Job Description:\n{job_desc}\n\n"
            f"HR Instructions:\n{hr_prompt}\n\n"
            f"Resume (id={resume_id}):\n{resume_text}\n\n"
            "Return JSON only with keys decision, category, match_score, rationale."
        )
        full_prompt = f"{SYSTEM_PROMPT}\n\n{human_section}"
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(full_prompt)
        text_out = getattr(response, "text", "") or ""
        usage_meta = getattr(response, "usage_metadata", None)
        if usage_meta:
            usage = {
                "prompt_tokens": getattr(usage_meta, "prompt_token_count", None) or usage_meta.get("prompt_token_count"),
                "response_tokens": getattr(usage_meta, "candidates_token_count", None) or usage_meta.get("candidates_token_count"),
                "total_tokens": getattr(usage_meta, "total_token_count", None) or usage_meta.get("total_token_count"),
            }
        else:
            usage = None
        return text_out, usage
    except Exception as e:  # Fallback to no usage on error
        return f"{{\"decision\": \"rejected\", \"rationale\": \"Gemini error: {str(e)}\"}}", None


def review_resumes(chain, job_desc: str, hr_prompt: str, resumes: Iterable[Tuple[int, str]], max_workers: int = 5, provider_name: str | None = None):
    """Review resumes in parallel for faster processing with categorization.

    Returns list of dicts with keys: resume_id, decision, rationale, category, match_score.
    Older callers expecting tuple should adapt (app updated separately).
    """
    resumes_list = list(resumes)
    results: List[Dict[str, Any]] = []
    
    engine, SessionLocal = init_db()
    migrate_schema(engine)
    provider = provider_name or getattr(chain, "__class__", type(chain)).__name__
    model_name = getattr(getattr(chain, "lc_attributes", None), "get", lambda *_: None)("model_name") if hasattr(chain, "lc_attributes") else "unknown"

    def process_single_resume(resume_id: int, text: str) -> Dict[str, Any]:
        """Process a single resume and return structured result."""
        try:
            prompt_payload = {
                "job_description": job_desc,
                "hr_prompt": hr_prompt or "",
                "resume_id": resume_id,
                "resume_text": text,
            }
            # If provider is google, perform native call for usage; else use chain.
            usage_info = None
            if (provider_name or "").lower() == "google":
                out, usage_info = _google_invoke_with_usage(job_desc, hr_prompt or "", resume_id, text)
                if not out:  # if empty fallback to chain
                    out = chain.invoke(prompt_payload)
            else:
                out = chain.invoke(prompt_payload)
            decision, rationale, category, match_score = _to_json_decision(out)
            # Usage logging removed.
            return {
                "resume_id": resume_id,
                "decision": decision,
                "rationale": rationale,
                "category": category,
                "match_score": match_score,
                **({"usage": usage_info} if usage_info else {}),
            }
        except Exception as e:
            return {
                "resume_id": resume_id,
                "decision": "rejected",
                "rationale": f"Error processing resume: {str(e)}",
                "category": "C",
                "match_score": None,
            }
    
    # Process resumes in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_resume = {
            executor.submit(process_single_resume, resume_id, text): resume_id
            for resume_id, text in resumes_list
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_resume):
            result = future.result()
            results.append(result)
    
    # Sort results by resume_id to maintain order
    results.sort(key=lambda x: x["resume_id"])
    return results
