import json
from typing import Iterable, List, Tuple
from config.settings import settings
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from .prompts import prompt


def _to_json_decision(text: str) -> Tuple[str, str]:
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
    rationale = str(data.get("rationale", ""))
    return decision, rationale


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
    chain = prompt | llm | StrOutputParser()
    return chain


def review_resumes(chain, job_desc: str, hr_prompt: str, resumes: Iterable[Tuple[int, str]]):
    results: List[Tuple[int, str, str]] = []
    for resume_id, text in resumes:
        out = chain.invoke({
            "job_description": job_desc,
            "hr_prompt": hr_prompt or "",
            "resume_id": resume_id,
            "resume_text": text,
        })
        decision, rationale = _to_json_decision(out)
        results.append((resume_id, decision, rationale))
    return results
