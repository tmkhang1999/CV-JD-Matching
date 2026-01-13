"""
Symbolic scoring module for CV-JD matching.
Provides rule-based scoring for exact requirement matching that semantic embeddings miss.

This addresses the limitation where semantic similarity measures textual closeness,
not requirement fulfillment. For example:
- "English intermediate" is semantically closer to "English fluent"
- But "Vietnamese native, English fluent IELTS 7.5" actually MEETS the requirement

Symbolic scoring evaluates:
1. Language requirement fulfillment (exact level matching)
2. Skill coverage (must-have vs nice-to-have)
3. Experience years alignment
4. Education requirements
"""
from typing import Dict, Any, List, Optional, Tuple


# Language proficiency levels in order (lower index = lower proficiency)
LANGUAGE_LEVELS = [
    "beginner", "elementary", "basic",
    "pre-intermediate", "lower-intermediate",
    "intermediate", "upper-intermediate",
    "advanced", "fluent", "native", "bilingual"
]

# Map various level names to normalized levels
LEVEL_NORMALIZATION = {
    # Basic levels
    "beginner": "beginner", "a1": "beginner",
    "elementary": "elementary", "a2": "elementary", "n5": "elementary", "jlpt n5": "elementary",
    "basic": "basic",
    # Intermediate levels
    "pre-intermediate": "pre-intermediate", "b1": "pre-intermediate", "n4": "pre-intermediate", "jlpt n4": "pre-intermediate",
    "lower-intermediate": "lower-intermediate",
    "intermediate": "intermediate", "b2": "intermediate", "n3": "intermediate", "jlpt n3": "intermediate",
    "upper-intermediate": "upper-intermediate",
    # Advanced levels
    "advanced": "advanced", "c1": "advanced", "n2": "advanced", "jlpt n2": "advanced",
    "fluent": "fluent", "c2": "fluent", "proficient": "fluent", "n1": "fluent", "jlpt n1": "fluent",
    "native": "native", "mother tongue": "native",
    "bilingual": "bilingual",
    # Business/Professional levels
    "business": "advanced", "professional": "advanced", "working proficiency": "advanced",
    # Conversational levels
    "conversational": "intermediate", "daily conversation": "intermediate",
    "limited working": "pre-intermediate", "survival": "elementary",
    # Japanese Language Proficiency Test full patterns
    "japanese language proficiency test level 1": "fluent",
    "japanese language proficiency test level 2": "advanced",
    "japanese language proficiency test level 3": "intermediate",
    "japanese language proficiency test level 4": "pre-intermediate",
    "japanese language proficiency test level 5": "elementary"
}


def normalize_language_level(level: str) -> str:
    """Normalize language level to standard form."""
    if not level:
        return "intermediate"  # default assumption
    level_lower = level.lower().strip()

    # Check for specific language certifications FIRST (before generic mappings)
    # IELTS/TOEFL scores that indicate proficiency
    if any(x in level_lower for x in ["ielts", "toefl", "toeic"]):
        # Extract score if present
        import re
        score_match = re.search(r'(\d+\.?\d*)', level_lower)
        if score_match:
            score = float(score_match.group(1))
            # IELTS scoring
            if "ielts" in level_lower:
                if score >= 8.0:
                    return "native"
                elif score >= 7.0:
                    return "fluent"
                elif score >= 6.0:
                    return "advanced"
                elif score >= 5.0:
                    return "intermediate"
                else:
                    return "elementary"
            # TOEFL iBT scoring
            elif "toefl" in level_lower:
                if score >= 110:
                    return "native"
                elif score >= 95:
                    return "fluent"
                elif score >= 80:
                    return "advanced"
                elif score >= 60:
                    return "intermediate"
                else:
                    return "elementary"
            # TOEIC scoring
            elif "toeic" in level_lower:
                if score >= 900:
                    return "fluent"
                elif score >= 785:
                    return "advanced"
                elif score >= 600:
                    return "intermediate"
                elif score >= 400:
                    return "pre-intermediate"
                else:
                    return "elementary"

    # Japanese language certifications
    if any(x in level_lower for x in ["jlpt", "japanese proficiency", "nihongo", "eju", "kanji kentei"]):
        import re
        # JLPT (Japanese Language Proficiency Test) - N1 to N5
        if "jlpt" in level_lower or "japanese proficiency" in level_lower or "nihongo" in level_lower:
            # Handle both "N1" style and "Level 1" style
            if ("n1" in level_lower) or ("level 1" in level_lower) or ("test 1" in level_lower) or ("test level 1" in level_lower):
                return "fluent"  # Near-native business level
            elif ("n2" in level_lower) or ("level 2" in level_lower) or ("test 2" in level_lower) or ("test level 2" in level_lower):
                return "advanced"  # Business level
            elif ("n3" in level_lower) or ("level 3" in level_lower) or ("test 3" in level_lower) or ("test level 3" in level_lower):
                return "intermediate"  # Daily conversation
            elif ("n4" in level_lower) or ("level 4" in level_lower) or ("test 4" in level_lower) or ("test level 4" in level_lower):
                return "pre-intermediate"  # Basic conversation
            elif ("n5" in level_lower) or ("level 5" in level_lower) or ("test 5" in level_lower) or ("test level 5" in level_lower):
                return "elementary"  # Basic phrases

        # EJU (Examination for Japanese University Admission)
        elif "eju" in level_lower:
            score_match = re.search(r'(\d+)', level_lower)
            if score_match:
                score = int(score_match.group(1))
                if score >= 320:
                    return "fluent"
                elif score >= 280:
                    return "advanced"
                elif score >= 240:
                    return "intermediate"
                elif score >= 200:
                    return "pre-intermediate"
                else:
                    return "elementary"

        # Kanji Kentei (Kanji proficiency test)
        elif "kanji kentei" in level_lower:
            if any(x in level_lower for x in ["1", "pre-1", "2"]):
                return "advanced"  # High kanji proficiency
            elif any(x in level_lower for x in ["3", "4", "5"]):
                return "intermediate"
            else:
                return "elementary"

    # Chinese language certifications
    if any(x in level_lower for x in ["hsk", "chinese proficiency", "hanyu"]):
        import re
        # HSK (Hanyu Shuiping Kaoshi) - Level 1 to 6
        if "hsk" in level_lower or "hanyu" in level_lower:
            level_match = re.search(r'(?:level\s*)?(\d+)', level_lower)
            if level_match:
                hsk_level = int(level_match.group(1))
                if hsk_level >= 6:
                    return "fluent"
                elif hsk_level >= 5:
                    return "advanced"
                elif hsk_level >= 4:
                    return "intermediate"
                elif hsk_level >= 3:
                    return "pre-intermediate"
                elif hsk_level >= 2:
                    return "elementary"
                else:
                    return "beginner"

    # European language certifications (DELF/DALF for French, DELE for Spanish, etc.)
    if any(x in level_lower for x in ["delf", "dalf", "dele", "telc", "goethe", "testdaf"]):
        import re
        # Most European frameworks use A1, A2, B1, B2, C1, C2
        if any(x in level_lower for x in ["c2", "proficiency"]):
            return "native"
        elif any(x in level_lower for x in ["c1"]) or ("dele c1" in level_lower) or ("dalf c1" in level_lower):
            return "fluent"
        elif any(x in level_lower for x in ["b2"]) or ("delf b2" in level_lower):
            return "advanced"
        elif any(x in level_lower for x in ["b1"]) or ("delf b1" in level_lower):
            return "intermediate"
        elif any(x in level_lower for x in ["a2"]) or ("delf a2" in level_lower):
            return "elementary"
        elif any(x in level_lower for x in ["a1"]) or ("delf a1" in level_lower):
            return "beginner"

    # Generic direct mapping (after specific certifications)
    for key, normalized in LEVEL_NORMALIZATION.items():
        if key in level_lower:
            return normalized

    return "intermediate"  # default


def get_level_score(level: str) -> int:
    """Get numeric score for a language level (0-10)."""
    normalized = normalize_language_level(level)
    try:
        return LANGUAGE_LEVELS.index(normalized)
    except ValueError:
        return 5  # intermediate default


def score_language_match(jd_languages: List[Dict], cv_languages: List[Dict]) -> Tuple[float, List[str]]:
    """
    Score language requirement match.

    Returns:
        (score: 0.0-1.0, details: list of match descriptions)
    """
    if not jd_languages:
        return 1.0, ["No language requirements specified"]

    if not cv_languages:
        return 0.0, ["Candidate has no languages listed"]

    # Build CV language lookup (name -> level_score)
    cv_lang_map = {}
    for lang in cv_languages:
        if lang and lang.get("name"):
            name = lang["name"].lower().strip()
            level = lang.get("level", "") or ""
            test_info = lang.get("test", {}) or {}

            # If there's test info, use it for more accurate level
            if test_info.get("name") and test_info.get("score"):
                level = f"{test_info['name']} {test_info['score']}"

            cv_lang_map[name] = {
                "level": level,
                "score": get_level_score(level)
            }

    total_requirements = len(jd_languages)
    met_requirements = 0
    details = []

    for req in jd_languages:
        if not req or not req.get("name"):
            continue

        req_name = req["name"].lower().strip()
        req_level = req.get("level", "") or ""
        req_score = get_level_score(req_level)

        # Find matching language in CV
        matched = False
        for cv_name, cv_info in cv_lang_map.items():
            # Check for language name match (fuzzy)
            if req_name in cv_name or cv_name in req_name:
                cv_score = cv_info["score"]

                if cv_score >= req_score:
                    met_requirements += 1
                    matched = True
                    details.append(f"[OK] {req_name}: required {req_level}, has {cv_info['level']}")
                else:
                    # Partial credit for close match
                    gap = req_score - cv_score
                    if gap <= 2:
                        met_requirements += 0.5
                        details.append(f"[PARTIAL] {req_name}: required {req_level}, has {cv_info['level']} (close)")
                    else:
                        details.append(f"[GAP] {req_name}: required {req_level}, has {cv_info['level']} (insufficient)")
                break

        if not matched and req_name not in [cv.lower() for cv in cv_lang_map.keys()]:
            details.append(f"[MISSING] {req_name}: required {req_level}, not listed in CV")

    score = met_requirements / total_requirements if total_requirements > 0 else 1.0
    return score, details


def normalize_skill_name(skill: str) -> str:
    """
    Normalize skill name for comparison.
    
    NOTE: Most normalization is now handled by GPT during extraction (see extraction_gpt.py).
    This function now only does basic cleanup for legacy or edge cases.
    """
    if not skill:
        return ""
    # Basic cleanup: lowercase and strip whitespace
    return skill.lower().strip()


def extract_cv_skills(cv_data: Dict[str, Any]) -> set:
    """Extract all skill names from CV."""
    skills = set()
    profile = cv_data.get("candidate_profile", {}) or {}
    skills_block = profile.get("skills", {}) or {}

    if isinstance(skills_block, dict):
        for category, skill_list in skills_block.items():
            if isinstance(skill_list, list):
                for item in skill_list:
                    if isinstance(item, dict):
                        name = item.get("name", "")
                    else:
                        name = str(item)
                    if name:
                        skills.add(normalize_skill_name(name))

    return skills


def extract_jd_skills(jd_data: Dict[str, Any]) -> Tuple[set, set]:
    """Extract must-have and nice-to-have skills from JD."""
    must_have = set()
    nice_to_have = set()

    profile = jd_data.get("job_profile", {}) or {}

    # From requirements
    requirements = profile.get("requirements", {}) or {}

    for req_item in requirements.get("must_have", []) or []:
        if isinstance(req_item, dict):
            for item in req_item.get("items", []) or []:
                if item:
                    must_have.add(normalize_skill_name(item))

    for req_item in requirements.get("nice_to_have", []) or []:
        if isinstance(req_item, dict):
            for item in req_item.get("items", []) or []:
                if item:
                    nice_to_have.add(normalize_skill_name(item))

    # From skills block
    skills_block = profile.get("skills", {}) or {}
    if isinstance(skills_block, dict):
        for category, skill_list in skills_block.items():
            if isinstance(skill_list, list):
                for skill in skill_list:
                    if skill:
                        # Skills listed in skills block are generally required
                        must_have.add(normalize_skill_name(skill))

    return must_have, nice_to_have


def score_skill_match(jd_data: Dict[str, Any], cv_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """
    Score skill requirement match.

    Returns:
        (score: 0.0-1.0, details: dict with matched/missing/bonus skills)
    """
    cv_skills = extract_cv_skills(cv_data)
    must_have, nice_to_have = extract_jd_skills(jd_data)

    if not must_have and not nice_to_have:
        return 1.0, {"note": "No skill requirements specified"}

    # Score must-have skills (critical)
    matched_must_have = set()
    missing_must_have = set()

    for skill in must_have:
        # Check for exact or partial match
        found = False
        for cv_skill in cv_skills:
            if skill in cv_skill or cv_skill in skill:
                matched_must_have.add(skill)
                found = True
                break
        if not found:
            missing_must_have.add(skill)

    # Score nice-to-have skills (bonus)
    matched_nice_to_have = set()
    for skill in nice_to_have:
        for cv_skill in cv_skills:
            if skill in cv_skill or cv_skill in skill:
                matched_nice_to_have.add(skill)
                break

    # Calculate score
    must_have_coverage = len(matched_must_have) / len(must_have) if must_have else 1.0
    nice_to_have_coverage = len(matched_nice_to_have) / len(nice_to_have) if nice_to_have else 0.0

    # Weighted score: must-have is 80%, nice-to-have is 20%
    score = (must_have_coverage * 0.8) + (nice_to_have_coverage * 0.2)

    details = {
        "must_have_coverage": round(must_have_coverage * 100, 1),
        "matched_must_have": list(matched_must_have)[:10],  # Limit for response size
        "missing_must_have": list(missing_must_have)[:10],
        "nice_to_have_coverage": round(nice_to_have_coverage * 100, 1),
        "matched_nice_to_have": list(matched_nice_to_have)[:5]
    }

    return score, details


def score_experience_match(jd_data: Dict[str, Any], cv_data: Dict[str, Any]) -> Tuple[float, str]:
    """
    Score experience years match.

    Returns:
        (score: 0.0-1.0, detail: description)
    """
    # Get JD requirement
    profile_jd = jd_data.get("job_profile", {}) or {}
    experience_req = profile_jd.get("experience", {}) or {}
    min_years_required = experience_req.get("min_years")

    if min_years_required is None:
        return 1.0, "No experience requirement specified"

    min_years_required = float(min_years_required)

    # Get CV experience
    profile_cv = cv_data.get("candidate_profile", {}) or {}
    headline = profile_cv.get("headline", {}) or {}
    cv_years = headline.get("total_years_of_experience")

    if cv_years is None:
        return 0.5, f"Experience not specified in CV (required: {min_years_required}+ years)"

    cv_years = float(cv_years)

    # Score based on match
    if cv_years >= min_years_required:
        if cv_years >= min_years_required * 1.5:
            return 1.0, f"Exceeds requirement: {cv_years} years (required: {min_years_required}+)"
        return 1.0, f"Meets requirement: {cv_years} years (required: {min_years_required}+)"
    else:
        # Partial score based on how close
        ratio = cv_years / min_years_required
        score = max(0.3, ratio)  # Minimum 30% if they have some experience
        return score, f"Below requirement: {cv_years} years (required: {min_years_required}+)"


def calculate_symbolic_score(jd_data: Dict[str, Any], cv_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive symbolic score for a CV-JD pair.

    This score complements semantic similarity by checking exact requirement fulfillment.

    Returns:
        {
            "total_score": 0.0-1.0,
            "language_score": 0.0-1.0,
            "skill_score": 0.0-1.0,
            "experience_score": 0.0-1.0,
            "details": {...}
        }
    """
    # Language matching
    jd_profile = jd_data.get("job_profile", {}) or {}
    jd_requirements = jd_profile.get("requirements", {}) or {}
    jd_languages = jd_requirements.get("languages", []) or []

    cv_profile = cv_data.get("candidate_profile", {}) or {}
    cv_languages = cv_profile.get("languages", []) or []

    lang_score, lang_details = score_language_match(jd_languages, cv_languages)

    # Skill matching
    skill_score, skill_details = score_skill_match(jd_data, cv_data)

    # Experience matching
    exp_score, exp_detail = score_experience_match(jd_data, cv_data)

    # Weighted total (configurable)
    weights = {
        "language": 0.25,
        "skill": 0.50,
        "experience": 0.25
    }

    total_score = (
        lang_score * weights["language"] +
        skill_score * weights["skill"] +
        exp_score * weights["experience"]
    )

    return {
        "total_score": round(total_score, 4),
        "language_score": round(lang_score, 4),
        "skill_score": round(skill_score, 4),
        "experience_score": round(exp_score, 4),
        "details": {
            "language": lang_details,
            "skills": skill_details,
            "experience": exp_detail
        }
    }


def combine_semantic_and_symbolic_scores(
    semantic_distance: float,
    symbolic_result: Dict[str, Any],
    semantic_weight: float = 0.5,
    symbolic_weight: float = 0.5
) -> float:
    """
    Combine semantic similarity and symbolic matching scores.

    Args:
        semantic_distance: Cosine distance from embeddings (0 = identical, 1 = orthogonal)
        symbolic_result: Result from calculate_symbolic_score
        semantic_weight: Weight for semantic score (default 0.5)
        symbolic_weight: Weight for symbolic score (default 0.5)

    Returns:
        Combined distance (0 = best match, 1 = worst match)
    """
    # Convert semantic distance to similarity (0-1, higher = better)
    semantic_similarity = 1.0 - min(1.0, semantic_distance)

    # Get symbolic score (already 0-1, higher = better)
    symbolic_similarity = symbolic_result.get("total_score", 0.5)

    # Combine similarities
    combined_similarity = (
        semantic_similarity * semantic_weight +
        symbolic_similarity * symbolic_weight
    )

    # Convert back to distance (lower = better)
    combined_distance = 1.0 - combined_similarity

    return round(combined_distance, 4)

