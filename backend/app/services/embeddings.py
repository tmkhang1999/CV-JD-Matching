from typing import Dict, Any, List
from openai import OpenAI
from sqlalchemy.orm import Session
import hashlib

from app.core.config import settings
from app.db import models

client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Cache for embeddings to avoid redundant API calls
_embedding_cache: Dict[str, List[float]] = {}


def _get_text_hash(text: str) -> str:
    """Generate a hash for text to use as cache key."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def create_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Create embeddings for multiple texts in a single API call for efficiency."""
    if not texts:
        return []

    # Prepare texts and track which need new embeddings
    processed_texts = []
    result_embeddings: List[List[float]] = []
    texts_to_embed = []
    text_indices = []

    for i, text in enumerate(texts):
        if not text.strip():
            text = " "

        text_hash = _get_text_hash(text)
        if text_hash in _embedding_cache:
            # Use cached embedding
            result_embeddings.append(_embedding_cache[text_hash])
        else:
            # Mark for new embedding
            result_embeddings.append([])  # Placeholder
            texts_to_embed.append(text)
            text_indices.append(i)

    # Get embeddings for new texts in batch
    if texts_to_embed:
        resp = client.embeddings.create(
            input=texts_to_embed,
            model=settings.OPENAI_EMBEDDING_MODEL,
        )
        new_embeddings = [data.embedding for data in resp.data]

        # Cache and assign new embeddings
        for idx, embedding in enumerate(new_embeddings):
            text = texts_to_embed[idx]
            text_hash = _get_text_hash(text)
            _embedding_cache[text_hash] = embedding
            result_i = text_indices[idx]
            result_embeddings[result_i] = embedding

    return result_embeddings


def create_embedding(text: str) -> List[float]:
    """Create embedding using OpenAI text-embedding-3-small model with caching."""
    if not text.strip():
        text = " "

    text_hash = _get_text_hash(text)
    if text_hash in _embedding_cache:
        return _embedding_cache[text_hash]

    resp = client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text,
    )
    embedding = resp.data[0].embedding
    _embedding_cache[text_hash] = embedding
    return embedding


# ---------- CV embedding builders ----------

def build_cv_global_text(structured: Dict[str, Any]) -> str:
    """Build comprehensive global text for CV using the actual CV schema."""
    candidate_profile = structured.get("candidate_profile", {}) or {}

    identity = candidate_profile.get("identity", {}) or {}
    headline = candidate_profile.get("headline", {}) or {}
    summary = candidate_profile.get("summary", "") or ""
    domain_expertise = candidate_profile.get("domain_expertise", []) or []
    experience = candidate_profile.get("experience", []) or []
    education = candidate_profile.get("education", []) or []

    # Identity fields
    name = identity.get("full_name", "") or ""
    location = identity.get("location", "") or ""

    # Headline fields
    current_position = headline.get("current_position", "") or ""
    seniority = headline.get("seniority", "") or ""
    years = headline.get("total_years_of_experience")

    parts = []

    # Professional identity
    if name:
        identity_parts = [name]
        if current_position:
            identity_parts.append(f"- {current_position}")
        parts.append(" ".join(identity_parts))

    # Experience level
    level_info = []
    if seniority:
        level_info.append(f"{seniority} level")
    if years is not None:
        level_info.append(f"{years} years experience")
    if level_info:
        parts.append(" | ".join(level_info))

    # Location
    if location:
        parts.append(f"Location: {location}")

    # Summary
    if summary:
        summary_short = summary[:300] + "..." if len(summary) > 300 else summary
        parts.append(f"Summary: {summary_short}")

    # Domain expertise
    if domain_expertise:
        parts.append(f"Domain expertise: {', '.join(domain_expertise)}")

    # Recent experience
    if experience:
        parts.append("\nRecent Experience:")
        for exp in experience[:3]:
            title = exp.get("title", "") or ""
            company = exp.get("company", "") or ""
            start_date = exp.get("start_date", "") or ""
            end_date = exp.get("end_date", "") or "Present"

            exp_line = f"- {title}"
            if company:
                exp_line += f" at {company}"
            if start_date:
                exp_line += f" ({start_date} - {end_date})"

            highlights = exp.get("highlights", []) or []
            if highlights:
                exp_line += f": {'; '.join(highlights[:2])}"
            parts.append(exp_line)

    # Education
    if education:
        edu = education[0]
        degree = edu.get("degree", "") or ""
        major = edu.get("major", "") or ""
        school = edu.get("school", "") or ""
        if degree or school:
            edu_text = "Education: "
            if degree and major:
                edu_text += f"{degree} in {major}"
            elif degree:
                edu_text += degree
            if school:
                edu_text += f" from {school}"
            parts.append(edu_text)

    return "\n".join(parts) if parts else "No profile information available"


def build_cv_skills_tech_text(structured: Dict[str, Any]) -> str:
    """Build comprehensive tech skills text using the actual CV schema."""
    candidate_profile = structured.get("candidate_profile", {}) or {}
    skills = candidate_profile.get("skills", {}) or {}
    experience = candidate_profile.get("experience", []) or []

    parts = []

    # Skill categories from the actual schema (SkillGroup)
    skill_categories = [
        ("programming_languages", "Programming Languages"),
        ("frameworks", "Frameworks"),
        ("databases", "Databases"),
        ("cloud_platforms", "Cloud Platforms"),
        ("tools_platforms", "Tools & Platforms"),
    ]

    # Add skills by category - each skill is a SkillItem with name, years_used, etc.
    for key, display_name in skill_categories:
        skill_list = skills.get(key, []) or []
        if skill_list:
            skill_names = []
            for skill in skill_list:
                if isinstance(skill, dict):
                    name = skill.get("name", "") or ""
                    years = skill.get("years_used")
                    if name:
                        if years:
                            skill_names.append(f"{name} ({years}y)")
                        else:
                            skill_names.append(name)
                elif isinstance(skill, str):
                    skill_names.append(skill)
            if skill_names:
                parts.append(f"{display_name}: {', '.join(skill_names)}")

    # Methodologies (list of strings)
    methodologies = skills.get("methodologies", []) or []
    if methodologies:
        parts.append(f"Methodologies: {', '.join(methodologies)}")

    # Tech stack from experience projects
    if experience:
        all_technologies = set()
        for exp in experience[:5]:
            projects = exp.get("projects", []) or []
            for proj in projects:
                technologies = proj.get("technologies", []) or []
                all_technologies.update(technologies)

        if all_technologies:
            parts.append(f"\nProject Technologies: {', '.join(sorted(all_technologies))}")

    return "\n".join(parts) if parts else "No technical skills specified"


def build_cv_skills_language_text(structured: Dict[str, Any]) -> str:
    """Build language skills text using the actual CV schema."""
    candidate_profile = structured.get("candidate_profile", {}) or {}
    languages = candidate_profile.get("languages", []) or []

    if not languages:
        return "Languages: Not specified"

    parts = ["Language Proficiency:"]
    for lang_info in languages:
        if isinstance(lang_info, dict):
            lang = lang_info.get("name", "") or ""
            level = lang_info.get("level", "") or ""
            test = lang_info.get("test", {}) or {}

            if lang:
                lang_line = f"- {lang}"
                if level:
                    lang_line += f" ({level})"
                if test:
                    test_name = test.get("name", "") or ""
                    test_score = test.get("score", "") or ""
                    if test_name and test_score:
                        lang_line += f" - {test_name}: {test_score}"
                parts.append(lang_line)

    return "\n".join(parts)


# ---------- JD embedding builders ----------

def build_jd_global_text(structured: Dict[str, Any]) -> str:
    """Build comprehensive global text for JD using the actual JD schema."""
    job_profile = structured.get("job_profile", {}) or {}

    title = job_profile.get("title", "") or ""
    level = job_profile.get("level", "") or ""
    domain = job_profile.get("domain", []) or []

    client = job_profile.get("client", {}) or {}
    client_name = client.get("name", "") or ""
    client_region = client.get("region", "") or ""

    employment = job_profile.get("employment", {}) or {}
    employment_type = employment.get("type", "") or ""
    working_mode = employment.get("working_mode", "") or ""
    location = employment.get("location", "") or ""
    remote_policy = employment.get("remote_policy", "") or ""

    experience = job_profile.get("experience", {}) or {}
    min_years = experience.get("min_years")
    seniority_notes = experience.get("seniority_notes", "") or ""

    responsibilities = job_profile.get("responsibilities", []) or []

    compensation = job_profile.get("compensation_benefits", {}) or {}
    salary_range = compensation.get("salary_range", "") or ""

    parts = []

    # Job identity
    if title:
        job_identity = [title]
        if level:
            job_identity.append(f"({level} Level)")
        parts.append(" ".join(job_identity))

    # Domain expertise
    if domain:
        parts.append(f"Domain: {', '.join(domain)}")

    # Client info
    if client_name:
        client_info = f"Client: {client_name}"
        if client_region:
            client_info += f" ({client_region})"
        parts.append(client_info)

    # Employment details
    emp_details = []
    if employment_type:
        emp_details.append(f"Type: {employment_type}")
    if working_mode:
        emp_details.append(f"Mode: {working_mode}")
    if location:
        emp_details.append(f"Location: {location}")
    if remote_policy:
        emp_details.append(f"Remote: {remote_policy}")
    if emp_details:
        parts.append(" | ".join(emp_details))

    # Experience requirements
    if min_years is not None:
        parts.append(f"Experience: {min_years}+ years")
    if seniority_notes:
        parts.append(f"Seniority: {seniority_notes}")

    # Salary if available
    if salary_range:
        parts.append(f"Salary: {salary_range}")

    # Key responsibilities (top 5)
    if responsibilities:
        parts.append("Key Responsibilities:")
        for resp in responsibilities[:5]:
            parts.append(f"- {resp}")

    return "\n".join(parts) if parts else "No job information available"


def build_jd_skills_tech_text(structured: Dict[str, Any]) -> str:
    """Build tech skills text using the actual JD schema with skills categories."""
    job_profile = structured.get("job_profile", {}) or {}
    skills = job_profile.get("skills", {}) or {}
    requirements = job_profile.get("requirements", {}) or {}

    parts = []

    # Skills by category from the actual schema
    skill_categories = [
        ("backend", "Backend"),
        ("frontend", "Frontend"),
        ("mobile", "Mobile"),
        ("database", "Database"),
        ("cloud_devops", "Cloud/DevOps"),
        ("data_ml", "Data/ML"),
        ("qa", "QA/Testing"),
        ("security", "Security"),
        ("architecture", "Architecture"),
        ("methodologies", "Methodologies"),
        ("tools", "Tools"),
    ]

    # Add skills by category
    has_skills = False
    for key, display_name in skill_categories:
        skill_list = skills.get(key, []) or []
        if skill_list:
            has_skills = True
            parts.append(f"{display_name}: {', '.join(skill_list)}")

    # Add must-have requirements
    must_have = requirements.get("must_have", []) or []
    if must_have:
        parts.append("\nMUST HAVE Requirements:")
        for req_item in must_have:
            if isinstance(req_item, dict):
                category = req_item.get("category", "") or ""
                items = req_item.get("items", []) or []
                if items:
                    if category:
                        parts.append(f"- {category}: {', '.join(items)}")
                    else:
                        parts.extend([f"- {item}" for item in items])

    # Add nice-to-have requirements
    nice_to_have = requirements.get("nice_to_have", []) or []
    if nice_to_have:
        parts.append("\nNICE TO HAVE:")
        for req_item in nice_to_have:
            if isinstance(req_item, dict):
                category = req_item.get("category", "") or ""
                items = req_item.get("items", []) or []
                if items:
                    if category:
                        parts.append(f"- {category}: {', '.join(items)}")
                    else:
                        parts.extend([f"- {item}" for item in items])

    if not parts:
        return "No technical skills specified"

    return "\n".join(parts)


def build_jd_skills_language_text(structured: Dict[str, Any]) -> str:
    """Build language requirements text using actual JD schema."""
    job_profile = structured.get("job_profile", {}) or {}
    requirements = job_profile.get("requirements", {}) or {}
    languages = requirements.get("languages", []) or []

    parts = []

    if languages:
        parts.append("Language Requirements:")
        for lang_info in languages:
            if isinstance(lang_info, dict):
                lang = lang_info.get("name", "") or ""
                level = lang_info.get("level", "") or ""
                test = lang_info.get("test", {}) or {}

                if lang:
                    lang_line = f"- {lang}"
                    if level:
                        lang_line += f" ({level})"
                    if test:
                        test_name = test.get("name", "") or ""
                        test_score = test.get("score", "") or ""
                        if test_name and test_score:
                            lang_line += f" - {test_name}: {test_score}"
                    parts.append(lang_line)

    return "\n".join(parts) if parts else "Languages: Not specified"


# ---------- Public API ----------

def update_document_embeddings(db: Session, doc: models.Document, structured: Dict[str, Any]) -> None:
    """
    Build all embeddings for a document and insert into document_embeddings with optimized batching.
    """
    # Ensure document has a valid ID
    if not doc.id:
        raise ValueError("Document must be saved with a valid ID before creating embeddings")

    # Remove old embeddings if we are re-processing
    db.query(models.DocumentEmbedding).filter(
        models.DocumentEmbedding.document_id == doc.id
    ).delete()

    if doc.type == "cv":
        global_text = build_cv_global_text(structured)
        skills_tech_text = build_cv_skills_tech_text(structured)
        skills_lang_text = build_cv_skills_language_text(structured)
    elif doc.type == "jd":
        global_text = build_jd_global_text(structured)
        skills_tech_text = build_jd_skills_tech_text(structured)
        skills_lang_text = build_jd_skills_language_text(structured)
    else:
        # Unknown type; skip
        return

    # Batch embedding creation for efficiency
    texts = [global_text, skills_tech_text, skills_lang_text]
    kinds = ["global", "skills_tech", "skills_language"]

    embeddings = create_embeddings_batch(texts)

    # Store embeddings with explicit document_id validation
    for kind, embedding in zip(kinds, embeddings):
        if not doc.id:  # Double-check document ID is still valid
            raise ValueError(f"Document ID became null during embedding creation for kind: {kind}")

        emb = models.DocumentEmbedding(
            document_id=doc.id,
            kind=kind,
            vector=embedding,
        )
        db.add(emb)

    # Note: Commit will be handled by the calling function


def clear_embedding_cache():
    """Clear the embedding cache to free memory."""
    global _embedding_cache
    _embedding_cache.clear()


def get_cache_stats() -> Dict[str, int]:
    """Get embedding cache statistics."""
    return {
        "cached_embeddings": len(_embedding_cache),
        "cache_size_mb": sum(len(str(v)) for v in _embedding_cache.values()) // (1024 * 1024)
    }
