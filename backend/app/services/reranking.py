"""
LLM-based reranking service for CV-JD matching.
Uses GPT to provide detailed analysis and scoring for top candidates.
Optimized for performance and cost with batch processing and concise prompts.
"""
import json
import concurrent.futures
from typing import List, Dict, Any
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Maximum candidates to rerank (controls API cost)
MAX_RERANK_CANDIDATES = 5


def extract_cv_summary(cv_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only relevant CV fields for LLM analysis to reduce tokens."""
    profile = cv_data.get("candidate_profile", {}) or {}

    identity = profile.get("identity", {}) or {}
    headline = profile.get("headline", {}) or {}
    skills = profile.get("skills", {}) or {}
    experience = profile.get("experience", []) or []
    languages = profile.get("languages", []) or []

    # Extract skill names only
    skill_names = {}
    for category, items in skills.items():
        if isinstance(items, list):
            names = []
            for item in items:
                if isinstance(item, dict):
                    names.append(item.get("name", ""))
                elif isinstance(item, str):
                    names.append(item)
            if names:
                skill_names[category] = [n for n in names if n]

    # Extract recent experience (last 3)
    recent_exp = []
    for exp in experience[:3]:
        if isinstance(exp, dict):
            recent_exp.append({
                "title": exp.get("title"),
                "company": exp.get("company"),
                "duration": f"{exp.get('start_date', '')} - {exp.get('end_date', 'Present')}",
                "highlights": (exp.get("highlights", []) or [])[:3]
            })

    return {
        "name": identity.get("full_name"),
        "position": headline.get("current_position"),
        "seniority": headline.get("seniority"),
        "years_experience": headline.get("total_years_of_experience"),
        "skills": skill_names,
        "recent_experience": recent_exp,
        "languages": [{"name": l.get("name"), "level": l.get("level")} for l in languages if l.get("name")],
        "domains": profile.get("domain_expertise", [])
    }


def extract_jd_summary(jd_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only relevant JD fields for LLM analysis to reduce tokens."""
    profile = jd_data.get("job_profile", {}) or {}

    requirements = profile.get("requirements", {}) or {}
    skills = profile.get("skills", {}) or {}
    experience = profile.get("experience", {}) or {}
    employment = profile.get("employment", {}) or {}

    # Extract must-have requirements
    must_have = []
    for req in requirements.get("must_have", []) or []:
        if isinstance(req, dict):
            items = req.get("items", [])
            if items:
                must_have.extend(items[:5])

    # Extract all skills
    all_skills = []
    for category, items in skills.items():
        if isinstance(items, list):
            all_skills.extend(items[:10])

    return {
        "title": profile.get("title"),
        "level": profile.get("level"),
        "domain": profile.get("domain"),
        "company": profile.get("client", {}).get("name") if profile.get("client") else None,
        "location": employment.get("location"),
        "working_mode": employment.get("working_mode"),
        "min_years": experience.get("min_years"),
        "must_have_requirements": must_have[:10],
        "required_skills": all_skills[:20],
        "languages": [{"name": l.get("name"), "level": l.get("level")}
                     for l in requirements.get("languages", []) if l.get("name")],
        "responsibilities": (profile.get("responsibilities", []) or [])[:5]
    }


def build_rerank_prompt(cv_summary: Dict[str, Any], jd_summary: Dict[str, Any],
                        match_type: str, vector_score_percent: int) -> str:
    """Build a concise, focused prompt for LLM reranking."""

    if match_type == "cv_to_jd":
        context = f"""Analyze how well this JOB matches this CANDIDATE.
        
CANDIDATE:
- Name: {cv_summary.get('name', 'Unknown')}
- Current Role: {cv_summary.get('position', 'N/A')} ({cv_summary.get('seniority', 'N/A')})
- Experience: {cv_summary.get('years_experience', 'N/A')} years
- Skills: {json.dumps(cv_summary.get('skills', {}), separators=(',', ':'))}
- Domains: {cv_summary.get('domains', [])}
- Languages: {cv_summary.get('languages', [])}

JOB:
- Title: {jd_summary.get('title', 'Unknown')}
- Level: {jd_summary.get('level', 'N/A')}
- Company: {jd_summary.get('company', 'N/A')}
- Required Years: {jd_summary.get('min_years', 'N/A')}+
- Must-Have: {jd_summary.get('must_have_requirements', [])}
- Skills: {jd_summary.get('required_skills', [])}
- Languages: {jd_summary.get('languages', [])}"""

    else:  # jd_to_cv
        context = f"""Analyze how well this CANDIDATE fits this JOB.

JOB REQUIREMENTS:
- Title: {jd_summary.get('title', 'Unknown')}
- Level: {jd_summary.get('level', 'N/A')}
- Required Years: {jd_summary.get('min_years', 'N/A')}+
- Must-Have: {jd_summary.get('must_have_requirements', [])}
- Skills: {jd_summary.get('required_skills', [])}
- Languages: {jd_summary.get('languages', [])}
- Key Responsibilities: {jd_summary.get('responsibilities', [])}

CANDIDATE:
- Name: {cv_summary.get('name', 'Unknown')}
- Current: {cv_summary.get('position', 'N/A')} ({cv_summary.get('seniority', 'N/A')})
- Experience: {cv_summary.get('years_experience', 'N/A')} years
- Skills: {json.dumps(cv_summary.get('skills', {}), separators=(',', ':'))}
- Languages: {cv_summary.get('languages', [])}
- Domains: {cv_summary.get('domains', [])}"""

    return f"""{context}

Vector similarity score: {vector_score_percent}%

Score this match from 0-100 based on:
1. Skills coverage (40%): How many required skills does the candidate have?
2. Experience fit (25%): Is experience level appropriate?
3. Domain relevance (20%): Industry/domain background match?
4. Language match (15%): Required language proficiency met?

Return JSON only:
{{"score": <0-100>, "explanation": "• Skills: [brief assessment] • Experience: [brief assessment] • Domain: [brief assessment] • Overall: [summary]"}}"""


def get_llm_analysis(prompt: str, fallback_score: int = 50) -> Dict[str, Any]:
    """Get LLM analysis with robust error handling and fallback."""
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_RERANKING_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior technical recruiter. Analyze CV-JD matches accurately and provide concise bullet-point analysis. Return valid JSON with explanation as a single string."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=400,  # Increased for bullet points
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content.strip()
        result = json.loads(content)

        score = int(result.get("score", fallback_score))
        score = max(0, min(100, score))

        explanation = result.get("explanation", "Analysis completed.")

        # Handle case where explanation is returned as a list (convert to bullet string)
        if isinstance(explanation, list):
            # Convert list to bullet points
            bullet_points = []
            for item in explanation:
                item_str = str(item).strip()
                if item_str:
                    if not item_str.startswith('•') and not item_str.startswith('-'):
                        item_str = f"• {item_str}"
                    bullet_points.append(item_str)
            explanation = " ".join(bullet_points)
        else:
            explanation = str(explanation)

        # Ensure we have bullet formatting if missing
        if explanation and not ('•' in explanation or '-' in explanation):
            # Try to format as bullets if it looks like separate points
            if '. ' in explanation and len(explanation.split('. ')) > 1:
                points = explanation.split('. ')
                explanation = " • ".join(f"{point.strip()}" for point in points if point.strip())

        # Truncate if too long
        if len(explanation) > 600:  # Increased limit for bullet points
            explanation = explanation[:597] + "..."

        return {"score": score, "explanation": explanation}

    except json.JSONDecodeError:
        return {"score": fallback_score, "explanation": "• Analysis: LLM response parsing failed, using vector score as fallback."}
    except Exception as e:
        return {"score": fallback_score, "explanation": f"• Error: Analysis unavailable - {str(e)[:80]}"}


def rerank_single_match(match_data: Dict[str, Any], source_data: Dict[str, Any],
                        match_type: str, source_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Rerank a single match. Used for parallel processing."""
    structured = match_data.get("structured", {})
    vector_score = match_data.get("final_score", match_data.get("base_score", 0.5))

    # Convert distance to similarity percentage for context
    vector_score_percent = max(0, min(100, int((1 - vector_score) * 100)))

    if match_type == "cv_to_jd":
        match_summary = extract_jd_summary(structured)
        prompt = build_rerank_prompt(source_summary, match_summary, match_type, vector_score_percent)
    else:
        match_summary = extract_cv_summary(structured)
        prompt = build_rerank_prompt(match_summary, source_summary, match_type, vector_score_percent)

    analysis = get_llm_analysis(prompt, fallback_score=vector_score_percent)

    return {
        "id": match_data["id"],
        "title": match_data.get("title", "Unknown"),
        "owner_name": match_data.get("owner_name", "Unknown"),
        "vector_score": vector_score_percent,
        "llm_score": analysis["score"],
        "explanation": analysis["explanation"],
        "structured": structured
    }


def rerank_jds_for_cv(cv_data: Dict[str, Any], jd_matches: List[Dict[str, Any]],
                      max_candidates: int = MAX_RERANK_CANDIDATES) -> List[Dict[str, Any]]:
    """
    Rerank JDs for a CV using parallel LLM analysis.

    Args:
        cv_data: Full CV structured JSON
        jd_matches: List of JD matches with vector scores
        max_candidates: Maximum number of candidates to rerank

    Returns:
        List of reranked results with LLM scores and explanations
    """
    # Limit candidates to control API cost
    candidates = jd_matches[:max_candidates]

    if not candidates:
        return []

    cv_summary = extract_cv_summary(cv_data)
    results = []

    # Process in parallel for better performance
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(rerank_single_match, match, cv_data, "cv_to_jd", cv_summary): match
            for match in candidates
        }

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                match = futures[future]
                # Fallback result on error
                results.append({
                    "id": match["id"],
                    "title": match.get("title", "Unknown"),
                    "owner_name": match.get("owner_name", "Unknown"),
                    "vector_score": int((1 - match.get("final_score", 0.5)) * 100),
                    "llm_score": int((1 - match.get("final_score", 0.5)) * 100),
                    "explanation": f"Reranking failed: {str(e)[:100]}",
                    "structured": match.get("structured", {})
                })

    # Sort by LLM score (descending)
    results.sort(key=lambda x: x["llm_score"], reverse=True)

    # Add final ranks
    for idx, result in enumerate(results):
        result["final_rank"] = idx + 1

    return results


def rerank_cvs_for_jd(jd_data: Dict[str, Any], cv_matches: List[Dict[str, Any]],
                      max_candidates: int = MAX_RERANK_CANDIDATES) -> List[Dict[str, Any]]:
    """
    Rerank CVs for a JD using parallel LLM analysis.

    Args:
        jd_data: Full JD structured JSON
        cv_matches: List of CV matches with vector scores
        max_candidates: Maximum number of candidates to rerank

    Returns:
        List of reranked results with LLM scores and explanations
    """
    # Limit candidates to control API cost
    candidates = cv_matches[:max_candidates]

    if not candidates:
        return []

    jd_summary = extract_jd_summary(jd_data)
    results = []

    # Process in parallel for better performance
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(rerank_single_match, match, jd_data, "jd_to_cv", jd_summary): match
            for match in candidates
        }

        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                match = futures[future]
                # Fallback result on error
                results.append({
                    "id": match["id"],
                    "title": match.get("title", "Unknown"),
                    "owner_name": match.get("owner_name", "Unknown"),
                    "vector_score": int((1 - match.get("final_score", 0.5)) * 100),
                    "llm_score": int((1 - match.get("final_score", 0.5)) * 100),
                    "explanation": f"Reranking failed: {str(e)[:100]}",
                    "structured": match.get("structured", {})
                })

    # Sort by LLM score (descending)
    results.sort(key=lambda x: x["llm_score"], reverse=True)

    # Add final ranks
    for idx, result in enumerate(results):
        result["final_rank"] = idx + 1

    return results

