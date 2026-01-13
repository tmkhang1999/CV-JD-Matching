from typing import Dict, Any, List

from app.schemas.cv import CVStructured, CandidateProfile, Identity as CVIdentity, Contact as CVContact, Headline as CVHeadline, SkillGroup as CVSkillGroup
from app.schemas.cv import ExperienceItem as CVExperienceItem, Project as CVProject
from app.schemas.cv import EducationItem as CVEducationItem, CertificationItem as CVCertificationItem, LanguageItem as CVLanguageItem, RawSection as CVRawSection
from app.schemas.jd import JDStructured, JobProfile, Client as JDClient, Employment as JDEmployment, Experience as JDExperience
from app.schemas.jd import Requirements as JDRequirements, RequirementItem as JDRequirementItem, LanguageRequirement as JDLanguageRequirement, Skills as JDSkills
from app.schemas.jd import CompensationBenefits as JDCompBenefits, Process as JDProcess, RawSection as JDRawSection

_ALLOWED_LANG_PROF = {"native", "fluent", "advanced", "intermediate", "basic"}
_ALLOWED_SENIORITY = {"entry", "junior", "mid", "senior", "lead", "principal", "architect", "director"}


def _normalize_string_list(items: Any) -> List[str]:
    if not isinstance(items, list):
        return []
    seen = set()
    result = []
    for item in items:
        if item is None:
            continue
        val = str(item).strip()
        if not val:
            continue
        key = val.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(val)
    return result


def _normalize_lang_items(lang_items: Any) -> List[Dict[str, Any]]:
    if not isinstance(lang_items, list):
        return []
    out = []
    for item in lang_items:
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        level = entry.get("level")
        if isinstance(level, str):
            lv = level.strip().lower()
            entry["level"] = lv if lv in _ALLOWED_LANG_PROF else level
        out.append(entry)
    return out


def _normalize_skill_items(skill_items: Any) -> List[Dict[str, Any]]:
    if not isinstance(skill_items, list):
        return []
    out = []
    seen = set()
    for item in skill_items:
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        name = entry.get("name")
        if not name:
            continue
        key = str(name).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        entry["name"] = name
        out.append(entry)
    return out


def normalize_cv(raw_structured: Dict[str, Any], raw_text: str) -> CVStructured:
    data = dict(raw_structured) if raw_structured else {}
    cp = data.get("candidate_profile", {}) if isinstance(data.get("candidate_profile"), dict) else {}

    identity_data = cp.get("identity", {}) if isinstance(cp.get("identity"), dict) else {}
    contact_data = identity_data.get("contact", {}) if isinstance(identity_data.get("contact"), dict) else {}
    headline_data = cp.get("headline", {}) if isinstance(cp.get("headline"), dict) else {}
    skills_data = cp.get("skills", {}) if isinstance(cp.get("skills"), dict) else {}

    # Normalize headline seniority
    seniority = headline_data.get("seniority")
    if isinstance(seniority, str):
        s = seniority.strip().lower()
        headline_data["seniority"] = s if s in _ALLOWED_SENIORITY else seniority

    # Normalize skills groups
    skills_data["programming_languages"] = _normalize_skill_items(skills_data.get("programming_languages", []))
    skills_data["frameworks"] = _normalize_skill_items(skills_data.get("frameworks", []))
    skills_data["databases"] = _normalize_skill_items(skills_data.get("databases", []))
    skills_data["cloud_platforms"] = _normalize_skill_items(skills_data.get("cloud_platforms", []))
    skills_data["tools_platforms"] = _normalize_skill_items(skills_data.get("tools_platforms", []))
    skills_data["methodologies"] = _normalize_string_list(skills_data.get("methodologies", []))

    # Normalize experiences and projects
    experience_raw = cp.get("experience", []) if isinstance(cp.get("experience"), list) else []
    experiences = []
    for exp in experience_raw:
        if not isinstance(exp, dict):
            continue
        exp_data = dict(exp)
        exp_data["highlights"] = _normalize_string_list(exp_data.get("highlights", []))
        projects_raw = exp_data.get("projects", []) if isinstance(exp_data.get("projects"), list) else []
        projects = []
        for proj in projects_raw:
            if not isinstance(proj, dict):
                continue
            proj_data = dict(proj)
            proj_data["domain"] = _normalize_string_list(proj_data.get("domain", []))
            proj_data["responsibilities"] = _normalize_string_list(proj_data.get("responsibilities", []))
            proj_data["technologies"] = _normalize_string_list(proj_data.get("technologies", []))
            proj_data["impacts_contributions"] = _normalize_string_list(proj_data.get("impacts_contributions", []))
            projects.append(CVProject(**proj_data))
        exp_data["projects"] = projects
        experiences.append(CVExperienceItem(**exp_data))

    education = [CVEducationItem(**edu) for edu in cp.get("education", []) if isinstance(edu, dict)]
    certifications = [CVCertificationItem(**cert) for cert in cp.get("certifications", []) if isinstance(cert, dict)]
    languages = [CVLanguageItem(**lang) for lang in _normalize_lang_items(cp.get("languages", []))]
    raw_sections = [CVRawSection(**sec) for sec in cp.get("raw_sections", []) if isinstance(sec, dict)]

    candidate_profile = CandidateProfile(
        identity=CVIdentity(
            full_name=identity_data.get("full_name"),
            location=identity_data.get("location"),
            contact=CVContact(**contact_data) if contact_data else None
        ),
        headline=CVHeadline(**headline_data) if headline_data else None,
        summary=cp.get("summary"),
        skills=CVSkillGroup(**skills_data),
        experience=experiences,
        education=education,
        certifications=certifications,
        languages=languages,
        domain_expertise=_normalize_string_list(cp.get("domain_expertise", [])),
        awards_achievements=_normalize_string_list(cp.get("awards_achievements", [])),
        activities=_normalize_string_list(cp.get("activities", [])),
        raw_sections=raw_sections
    )

    return CVStructured(candidate_profile=candidate_profile)


def normalize_jd(raw_structured: Dict[str, Any], raw_text: str) -> JDStructured:
    data = dict(raw_structured) if raw_structured else {}
    jp = data.get("job_profile", {}) if isinstance(data.get("job_profile"), dict) else {}

    requirements_raw = jp.get("requirements", {}) if isinstance(jp.get("requirements"), dict) else {}
    must_have = [JDRequirementItem(**req) for req in requirements_raw.get("must_have", []) if isinstance(req, dict)]
    nice_to_have = [JDRequirementItem(**req) for req in requirements_raw.get("nice_to_have", []) if isinstance(req, dict)]
    education = _normalize_string_list(requirements_raw.get("education", []))
    languages = [JDLanguageRequirement(**lang) for lang in _normalize_lang_items(requirements_raw.get("languages", []))]

    skills_raw = jp.get("skills", {}) if isinstance(jp.get("skills"), dict) else {}
    skills = JDSkills(**{k: _normalize_string_list(skills_raw.get(k, [])) for k in JDSkills.__fields__.keys()})

    raw_sections = [JDRawSection(**sec) for sec in jp.get("raw_sections", []) if isinstance(sec, dict)]

    job_profile = JobProfile(
        title=jp.get("title"),
        level=jp.get("level"),
        domain=_normalize_string_list(jp.get("domain", [])),
        client=JDClient(**jp.get("client", {})) if isinstance(jp.get("client"), dict) else None,
        employment=JDEmployment(**jp.get("employment", {})) if isinstance(jp.get("employment"), dict) else None,
        experience=JDExperience(**jp.get("experience", {})) if isinstance(jp.get("experience"), dict) else None,
        responsibilities=_normalize_string_list(jp.get("responsibilities", [])),
        requirements=JDRequirements(
            must_have=must_have,
            nice_to_have=nice_to_have,
            education=education,
            languages=languages
        ),
        skills=skills,
        compensation_benefits=JDCompBenefits(**jp.get("compensation_benefits", {})) if isinstance(jp.get("compensation_benefits"), dict) else None,
        process=JDProcess(**jp.get("process", {})) if isinstance(jp.get("process"), dict) else None,
        raw_sections=raw_sections
    )

    return JDStructured(job_profile=job_profile)
