import json
from typing import Dict, Any
from openai import OpenAI
from app.core.config import settings

# OpenAI client for extraction
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def _build_minimal_structure(doc_type: str) -> Dict[str, Any]:
    dt = (doc_type or "").lower()
    if dt == "jd":
        return {
            "job_profile": {
                "title": "Unknown",
                "level": "junior",
                "domain": [],
                "client": {"name": None, "region": None},
                "employment": {
                    "type": None,
                    "working_mode": None,
                    "location": None,
                    "work_hours": None,
                    "remote_policy": None
                },
                "experience": {"min_years": 0, "seniority_notes": None},
                "responsibilities": [],
                "requirements": {
                    "must_have": [],
                    "nice_to_have": [],
                    "education": [],
                    "languages": []
                },
                "skills": {
                    "backend": [],
                    "frontend": [],
                    "mobile": [],
                    "database": [],
                    "cloud_devops": [],
                    "data_ml": [],
                    "qa": [],
                    "security": [],
                    "architecture": [],
                    "methodologies": [],
                    "tools": []
                },
                "compensation_benefits": {
                    "salary_range": None,
                    "bonus": None,
                    "allowances": [],
                    "insurance": [],
                    "pto": None,
                    "other_benefits": []
                },
                "process": {"interview_steps": [], "start_date": None},
                "raw_sections": []
            }
        }
    return {
        "candidate_profile": {
            "identity": {"full_name": "Unknown", "location": None, "contact": {"email": None, "phone": None, "links": []}},
            "headline": {"current_position": None, "seniority": "junior", "total_years_of_experience": 0},
            "summary": None,
            "skills": {
                "programming_languages": [],
                "frameworks": [],
                "databases": [],
                "cloud_platforms": [],
                "tools_platforms": [],
                "methodologies": []
            },
            "experience": [],
            "education": [],
            "certifications": [],
            "languages": [],
            "domain_expertise": [],
            "awards_achievements": [],
            "activities": [],
            "raw_sections": []
        }
    }


def _safe_parse_json(content: str, doc_type: str) -> Dict[str, Any]:
    """Safely parse JSON from LLM response, handling markdown code blocks and malformed JSON."""
    content = content.strip()

    # Remove markdown code block wrapper if present
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:].strip()

    # Try parsing the JSON as-is first
    try:
        parsed_data = json.loads(content)
    except json.JSONDecodeError as e:
        # If parsing fails, try to fix common JSON issues
        try:
            # Remove any trailing commas before closing brackets/braces
            import re
            content = re.sub(r',(\s*[}\]])', r'\1', content)

            # Fix missing quotes around keys
            content = re.sub(r'(\w+):', r'"\1":', content)

            # Try parsing again
            parsed_data = json.loads(content)
        except json.JSONDecodeError:
            # If still failing, try to extract JSON from the middle of the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_content = content[json_start:json_end]
                try:
                    parsed_data = json.loads(json_content)
                except json.JSONDecodeError:
                    print(f"Warning: Failed to parse GPT JSON response. Error: {str(e)}")
                    print(f"Content: {content[:500]}...")
                    return _build_minimal_structure(doc_type)
            else:
                print(f"Warning: Failed to parse GPT JSON response. Error: {str(e)}")
                print(f"Content: {content[:500]}...")
                return _build_minimal_structure(doc_type)

    # Fix None values in technical skills to prevent Pydantic validation errors
    def fix_tech_skills(skills_dict):
        """Convert None values to empty lists in technical skills"""
        if not isinstance(skills_dict, dict):
            return skills_dict

        tech_skill_fields = [
            "programming_languages", "frameworks_libraries", "databases",
            "cloud_platforms", "devops_tools", "development_tools",
            "testing_frameworks", "other_technologies"
        ]
        for field in tech_skill_fields:
            if field in skills_dict and skills_dict[field] is None:
                skills_dict[field] = []
        return skills_dict

    # Apply fixes to technical skills fields in both CV and JD formats
    if "technical_skills" in parsed_data:
        parsed_data["technical_skills"] = fix_tech_skills(parsed_data["technical_skills"])

    if "technical_requirements" in parsed_data:
        if "must_have_skills" in parsed_data["technical_requirements"]:
            parsed_data["technical_requirements"]["must_have_skills"] = fix_tech_skills(
                parsed_data["technical_requirements"]["must_have_skills"]
            )
        if "nice_to_have_skills" in parsed_data["technical_requirements"]:
            parsed_data["technical_requirements"]["nice_to_have_skills"] = fix_tech_skills(
                parsed_data["technical_requirements"]["nice_to_have_skills"]
            )

    return parsed_data


# Common schema components to avoid duplication
def _get_tech_skills_schema() -> Dict[str, Any]:
    """Standardized technical skills schema used across CV and JD."""
    return {
        "programming_languages": ["string (Python, Java, JavaScript, TypeScript, C#, Go, etc.)"],
        "frameworks_libraries": ["string (React, Angular, Vue, Spring Boot, Django, .NET, etc.)"],
        "databases": ["string (MySQL, PostgreSQL, MongoDB, Redis, Oracle, etc.)"],
        "cloud_platforms": ["string (AWS, Azure, Google Cloud, IBM Cloud, etc.)"],
        "devops_tools": ["string (Docker, Kubernetes, Jenkins, GitLab CI, Terraform, etc.)"],
        "development_tools": ["string (Git, VS Code, IntelliJ, Postman, Swagger, etc.)"],
        "testing_frameworks": ["string (Jest, JUnit, Pytest, Selenium, Cypress, etc.)"],
        "other_technologies": ["string (other relevant technical skills)"]
    }


def _get_language_skill_schema() -> Dict[str, Any]:
    """Standardized language skill schema."""
    return {
        "language": "string",
        "proficiency_level": "string (native | fluent | advanced | intermediate | basic)",
        "certificate_type": "string (IELTS, TOEIC, JLPT, DELF, etc.)",
        "certificate_score": "string",
        "years_experience": "number"
    }


def _get_location_schema() -> Dict[str, Any]:
    """Standardized location schema."""
    return {
        "city": "string",
        "country": "string",
        "is_remote_available": "boolean"
    }


def build_cv_schema() -> Dict[str, Any]:
    """
    Lean CV extraction schema focusing on high-signal fields for matching.
    """
    return {
        "candidate_profile": {
            "identity": {
                "full_name": "string",
                "location": "string",
                "contact": {"email": "string", "phone": "string", "links": ["string"]}
            },
            "headline": {
                "current_position": "string",
                "seniority": "entry | junior | mid | senior | lead | principal | architect | director",
                "total_years_of_experience": "number"
            },
            "summary": "string",
            "skills": {
                "programming_languages": [{"name": "string", "years_used": "number", "last_used_year": "number", "proficiency": "string"}],
                "frameworks": [{"name": "string"}],
                "databases": [{"name": "string"}],
                "cloud_platforms": [{"name": "string", "services": ["string"]}],
                "tools_platforms": [{"name": "string"}],
                "methodologies": ["string"]
            },
            "experience": [{
                "company": "string",
                "title": "string",
                "start_date": "string (YYYY-MM)",
                "end_date": "string (YYYY-MM or 'current')",
                "location": "string",
                "highlights": ["string"],
                "projects": [{
                    "project_name": "string",
                    "domain": ["string"],
                    "role": "string",
                    "team_size": "string",
                    "description": "string",
                    "responsibilities": ["string"],
                    "technologies": ["string"],
                    "impacts_contributions": ["string"]
                }]
            }],
            "education": [{"school": "string", "degree": "string", "major": "string", "start_year": "number", "end_year": "number"}],
            "certifications": [{"name": "string", "issuer": "string", "year": "number", "credential_url": "string"}],
            "languages": [{"name": "string", "level": "string", "test": {"name": "string", "score": "string"}}],
            "domain_expertise": ["string"],
            "awards_achievements": ["string"],
            "activities": ["string"],
            "raw_sections": [{"section_title": "string", "content": "string"}]
        }
    }


def build_jd_schema() -> Dict[str, Any]:
    """
    Lean JD extraction schema focusing on matching-critical fields.
    """
    return {
        "job_profile": {
            "title": "string",
            "level": "string",
            "domain": ["string"],
            "client": {"name": "string", "region": "string"},
            "employment": {
                "type": "string",
                "working_mode": "string",
                "location": "string",
                "work_hours": "string",
                "remote_policy": "string"
            },
            "experience": {"min_years": "number", "seniority_notes": "string"},
            "responsibilities": ["string"],
            "requirements": {
                "must_have": [{"category": "string", "items": ["string"]}],
                "nice_to_have": [{"category": "string", "items": ["string"]}],
                "education": ["string"],
                "languages": [{"name": "string", "level": "string", "test": {"name": "string", "score": "string"}}]
            },
            "skills": {
                "backend": ["string"],
                "frontend": ["string"],
                "mobile": ["string"],
                "database": ["string"],
                "cloud_devops": ["string"],
                "data_ml": ["string"],
                "qa": ["string"],
                "security": ["string"],
                "architecture": ["string"],
                "methodologies": ["string"],
                "tools": ["string"]
            },
            "compensation_benefits": {
                "salary_range": "string",
                "bonus": "string",
                "allowances": ["string"],
                "insurance": ["string"],
                "pto": "string",
                "other_benefits": ["string"]
            },
            "process": {"interview_steps": ["string"], "start_date": "string"},
            "raw_sections": [{"section_title": "string", "content": "string"}]
        }
    }


def extract_with_gpt(raw_text: str, schema: Dict[str, Any], doc_type: str) -> Dict[str, Any]:
    """
    Extract structured data from raw text using GPT-4.1-mini.

    Args:
        raw_text: The raw document text
        schema: The JSON schema to follow
        doc_type: Either "CV" or "JD"

    Returns:
        Structured data as dictionary
    """
    schema_str = json.dumps(schema, indent=2)

    system_prompt = f"""You are an expert at extracting structured information from {doc_type} documents.
Extract all relevant information from the provided text and return it in the exact JSON format specified.

IMPORTANT RULES:
1. Return ONLY valid JSON, no additional text or explanation
2. Follow the schema structure exactly
3. Use null for missing values, not empty strings
4. Extract skills, technologies, and domains accurately
5. Normalize seniority levels to: junior, mid, senior, lead, or architect
6. Normalize role categories to: backend, frontend, fullstack, mobile, devops, qa, ba, pm, designer, or other
7. Normalize language proficiency to: native, fluent, advanced, intermediate, or basic
8. Be comprehensive - extract all mentioned skills, responsibilities, and experience

CRITICAL - SKILL NORMALIZATION:
When extracting skills and technologies, normalize them to their canonical form for better matching:
- Use standard naming: "React" not "React.js" or "ReactJS", "Node" not "Node.js" or "NodeJS"
- Abbreviate common terms: "JavaScript" → "JS", "TypeScript" → "TS", "Kubernetes" → "K8s"
- Standardize cloud providers: "Amazon Web Services" → "AWS", "Google Cloud Platform" → "GCP"
- Normalize databases: "PostgreSQL" → "Postgres", "MongoDB" → "Mongo"
- Unify variants: ".NET" / "DotNet" → "dotnet", "C#" → "csharp", "C++" → "cpp"
- Keep frameworks consistent: "Vue.js" → "Vue", "Angular.js" → "Angular"
- Use the most common industry name for each technology
- Apply the same normalization rules consistently across both CV and JD to ensure matching works

Schema to follow:
{schema_str}"""

    user_prompt = f"""Extract structured information from this {doc_type}:

{raw_text}

Return the extracted data in JSON format following the provided schema."""

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_EXTRACTION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # temperature=settings.openai.temperature,
            # max_completion_tokens=settings.openai.max_completion_tokens,
        )

        content = response.choices[0].message.content
        return _safe_parse_json(content, doc_type)

    except Exception as e:
        raise Exception(f"Failed to extract {doc_type} with GPT-4.1-mini: {str(e)}")


def extract_cv_structured(raw_text: str) -> Dict[str, Any]:
    """Extract structured data from CV text using GPT-4.1-mini."""
    schema = build_cv_schema()
    return extract_with_gpt(raw_text, schema, "CV")


def extract_jd_structured(raw_text: str) -> Dict[str, Any]:
    """Extract structured data from JD text using GPT-4.1-mini."""
    schema = build_jd_schema()
    return extract_with_gpt(raw_text, schema, "JD")
