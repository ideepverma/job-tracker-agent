"""
cover_letter.py — Generates a tailored cover letter draft per job, for free,
using a template filled with your config.yaml details. No paid API needed.

Optional upgrade: if you have Ollama (https://ollama.com, free, runs
locally) installed with a model pulled (e.g. `ollama pull llama3.1`),
set use_ollama=True in generate() to get a more tailored draft using
your own local LLM — still $0, nothing leaves your machine.
"""
import requests

TEMPLATE = """Dear Hiring Team at {company},

I'm writing to apply for the {title} position. I'm a {headline}, and I
believe my background aligns well with what you're looking for.

A few highlights from my experience:
{skills_block}

{achievement}

I hold a {education}, and you can see more of my work here: {portfolio}

I'd welcome the chance to discuss how I can contribute to {company}'s
engineering team. Thank you for your time and consideration.

Best regards,
{name}
"""


def _template_letter(job, candidate):
    skills_block = "\n".join(f"- {s}" for s in candidate.get("key_skills", []))
    return TEMPLATE.format(
        company=job.get("company", "your company"),
        title=job.get("title", "this role"),
        headline=candidate.get("headline", ""),
        skills_block=skills_block,
        achievement=candidate.get("achievement", ""),
        education=candidate.get("education", ""),
        portfolio=candidate.get("portfolio_url", ""),
        name=candidate.get("name", ""),
    )


def _ollama_letter(job, candidate, model="llama3.1"):
    """Optional: use a free local LLM via Ollama for a sharper draft."""
    prompt = f"""Write a concise, specific 4-paragraph cover letter for this job:
Title: {job.get('title')}
Company: {job.get('company')}

Candidate background:
- Headline: {candidate.get('headline')}
- Skills: {', '.join(candidate.get('key_skills', []))}
- Key achievement: {candidate.get('achievement')}
- Education: {candidate.get('education')}
- Portfolio: {candidate.get('portfolio_url')}
- Name: {candidate.get('name')}

Keep it professional, no fluff, no placeholder brackets."""
    try:
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"[cover_letter] Ollama unavailable ({e}), falling back to template.")
        return _template_letter(job, candidate)


def generate(job, candidate, use_ollama=False, ollama_model="llama3.1"):
    if use_ollama:
        return _ollama_letter(job, candidate, ollama_model)
    return _template_letter(job, candidate)
