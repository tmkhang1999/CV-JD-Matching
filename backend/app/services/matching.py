from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.services.symbolic_scoring import calculate_symbolic_score, combine_semantic_and_symbolic_scores


def calculate_adaptive_weights(structured_data: Dict[str, Any], doc_type: str) -> Dict[str, float]:
    """Calculate adaptive weights based on job requirements or CV characteristics."""
    cfg_default = settings.matching.weights
    default_weights = {"global": cfg_default.global_, "skills_tech": cfg_default.skills_tech, "skills_language": cfg_default.skills_language}

    try:
        if not structured_data:
            return default_weights

        if doc_type == "jd":
            jp = structured_data.get("job_profile", {}) or {}
            skills_block = jp.get("skills", {}) or {}
            tech_count = 0
            if isinstance(skills_block, dict):
                tech_count = sum(len(v or []) for v in skills_block.values())
            reqs = jp.get("requirements", {}) or {}
            lang_req = reqs.get("languages", []) or []

            if tech_count > 15:
                return {"global": 0.2, "skills_tech": 0.65, "skills_language": 0.15}
            elif tech_count > 8:
                return {"global": 0.25, "skills_tech": 0.6, "skills_language": 0.15}
            elif len(lang_req) > 2:
                return {"global": 0.25, "skills_tech": 0.4, "skills_language": 0.35}

        elif doc_type == "cv":
            cp = structured_data.get("candidate_profile", {}) or {}
            skills = cp.get("skills", {}) or {}
            experience = cp.get("experience", []) or []
            tech_count = 0
            if isinstance(skills, dict):
                for v in skills.values():
                    if isinstance(v, list):
                        tech_count += len(v)
            project_count = 0
            for exp in experience:
                projs = exp.get("projects") if isinstance(exp, dict) else None
                if isinstance(projs, list):
                    project_count += len([p for p in projs if p])

            if tech_count > 20 or project_count > 5:
                return {"global": 0.2, "skills_tech": 0.7, "skills_language": 0.1}
            elif tech_count > 10:
                return {"global": 0.25, "skills_tech": 0.6, "skills_language": 0.15}

    except Exception as e:
        print(f"Warning: Error in calculate_adaptive_weights: {str(e)}")
        print(f"Falling back to default weights for doc_type: {doc_type}")

    return default_weights


def build_enhanced_filter_conditions(filters: Optional[Dict[str, Any]], target_type: str) -> str:
    """Build enhanced SQL WHERE conditions with better performance and accuracy."""
    conditions = [f"d.type = '{target_type}'"]

    if not filters:
        return " AND ".join(conditions)

    # Filter by experience range with better logic (new schema paths)
    if filters.get("min_years") is not None or filters.get("max_years") is not None:
        min_years = filters.get("min_years")
        max_years = filters.get("max_years")
        if min_years is None:
            min_years = 0
        if max_years is None:
            max_years = 50
        min_years = int(min_years)
        max_years = int(max_years)

        if target_type == "cv":
            conditions.append(f"""
                COALESCE((d.structured->'candidate_profile'->'headline'->>'total_years_of_experience')::float, 0)
                BETWEEN {min_years} AND {max_years}
            """)
        else:
            conditions.append(f"""
                COALESCE((d.structured->'job_profile'->'experience'->>'min_years')::float, 0) <= {max_years}
                AND {min_years} <= COALESCE((d.structured->'job_profile'->'experience'->>'min_years')::float, 50)
            """)

    # Enhanced skills filtering with category support (new schema shapes)
    if filters.get("required_skills"):
        skills = filters["required_skills"]
        skill_conditions = []

        if target_type == "cv":
            for skill in skills:
                skill_conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM jsonb_each(d.structured->'candidate_profile'->'skills') AS cat(category, skill_list)
                        WHERE jsonb_typeof(skill_list) = 'array'
                        AND EXISTS (
                            SELECT 1 FROM jsonb_array_elements(skill_list) AS skill_obj
                            WHERE LOWER(skill_obj->>'name') LIKE LOWER('%{skill}%')
                        )
                    )
                """)
        else:
            for skill in skills:
                skill_conditions.append(f"""
                    (EXISTS (
                        SELECT 1 FROM jsonb_array_elements(d.structured->'job_profile'->'requirements'->'must_have') AS req
                        WHERE EXISTS (
                            SELECT 1 FROM jsonb_array_elements_text(req->'items') AS itm
                            WHERE LOWER(itm) LIKE LOWER('%{skill}%')
                        )
                    ) OR EXISTS (
                        SELECT 1 FROM jsonb_array_elements(d.structured->'job_profile'->'requirements'->'nice_to_have') AS req
                        WHERE EXISTS (
                            SELECT 1 FROM jsonb_array_elements_text(req->'items') AS itm
                            WHERE LOWER(itm) LIKE LOWER('%{skill}%')
                        )
                    ) OR EXISTS (
                        SELECT 1 FROM jsonb_each(d.structured->'job_profile'->'skills') AS cat(category, skill_list)
                        WHERE jsonb_typeof(skill_list) = 'array'
                        AND EXISTS (
                            SELECT 1 FROM jsonb_array_elements_text(skill_list) AS itm
                            WHERE LOWER(itm) LIKE LOWER('%{skill}%')
                        )
                    ))
                """)

        if skill_conditions:
            conditions.append("(" + " AND ".join(skill_conditions) + ")")

    # Domain filtering
    if filters.get("domains"):
        domains = filters["domains"]
        if target_type == "cv":
            domain_condition = f"""
                EXISTS (
                    SELECT 1 FROM jsonb_array_elements_text(d.structured->'candidate_profile'->'domain_expertise') AS domain
                    WHERE domain = ANY(ARRAY{domains})
                )
            """
        else:
            domain_condition = f"""
                EXISTS (
                    SELECT 1 FROM jsonb_array_elements_text(d.structured->'job_profile'->'domain') AS domain
                    WHERE domain = ANY(ARRAY{domains})
                )
            """
        conditions.append(domain_condition)

    # Seniority/level filtering
    if filters.get("seniority"):
        seniority_levels = filters["seniority"]
        if isinstance(seniority_levels, str):
            seniority_levels = [seniority_levels]
        if target_type == "cv":
            conditions.append(f"""
                LOWER(d.structured->'candidate_profile'->'headline'->>'seniority') = ANY(ARRAY{[s.lower() for s in seniority_levels]})
            """)
        else:
            conditions.append(f"""
                LOWER(d.structured->'job_profile'->>'level') = ANY(ARRAY{[s.lower() for s in seniority_levels]})
            """)

    return " AND ".join(conditions)


def cv_to_jd_matches(
    db: Session,
    cv_id: int,
    filters: Optional[Dict[str, Any]] = None,
    weights: Optional[Dict[str, float]] = None,
    limit: int = 10,
    use_adaptive_weights: bool = True
) -> List[Dict[str, Any]]:
    """
    Find best matching JDs for a given CV using optimized vector similarity with adaptive weighting.
    """
    cfg_default = settings.matching.weights
    default_weights = {"global": cfg_default.global_, "skills_tech": cfg_default.skills_tech, "skills_language": cfg_default.skills_language}

    # First, verify that the source CV has embeddings
    embedding_check = db.execute(
        text("""
            SELECT kind, CASE WHEN vector IS NOT NULL THEN true ELSE false END as has_vector
            FROM document_embeddings 
            WHERE document_id = :cv_id
        """),
        {"cv_id": cv_id}
    ).fetchall()

    if not embedding_check:
        print(f"Warning: CV {cv_id} has no embeddings stored in database")
        return []

    embedding_status = {row.kind: row.has_vector for row in embedding_check}
    required_kinds = ["global", "skills_tech", "skills_language"]
    missing_kinds = [k for k in required_kinds if k not in embedding_status or not embedding_status.get(k)]

    if missing_kinds:
        print(f"Warning: CV {cv_id} is missing embeddings for: {missing_kinds}")
        return []

    # Get CV data for adaptive weighting
    cv_data = {}
    if use_adaptive_weights:
        try:
            cv_result = db.execute(
                text("SELECT structured FROM documents WHERE id = :cv_id"),
                {"cv_id": cv_id}
            ).fetchone()
            if cv_result:
                cv_data = cv_result.structured
        except Exception as e:
            print(f"Warning: Could not retrieve CV data for adaptive weighting: {e}")

    # Calculate weights with robust validation
    if weights and isinstance(weights, dict) and all(key in weights for key in ["global", "skills_tech", "skills_language"]):
        final_weights = weights
    elif use_adaptive_weights and cv_data:
        try:
            calculated_weights = calculate_adaptive_weights(cv_data, "cv")
            if isinstance(calculated_weights, dict) and all(key in calculated_weights for key in ["global", "skills_tech", "skills_language"]):
                final_weights = calculated_weights
            else:
                print("Warning: Invalid weights returned from calculate_adaptive_weights, using defaults")
                final_weights = default_weights
        except Exception as e:
            print(f"Warning: Error calculating adaptive weights: {e}")
            final_weights = default_weights
    else:
        final_weights = default_weights

    # Extract weights with additional safety checks
    w_global = final_weights.get("global", 0.3)
    w_skills = final_weights.get("skills_tech", 0.5)
    w_lang = final_weights.get("skills_language", 0.2)

    filter_conditions = build_enhanced_filter_conditions(filters, "jd")

    sql = text(f"""
        WITH cv_emb AS (
            SELECT
                (SELECT vector FROM document_embeddings WHERE document_id = :cv_id AND kind = 'global') AS v_global,
                (SELECT vector FROM document_embeddings WHERE document_id = :cv_id AND kind = 'skills_tech') AS v_skills_tech,
                (SELECT vector FROM document_embeddings WHERE document_id = :cv_id AND kind = 'skills_language') AS v_skills_lang
        ),
        scored_matches AS (
            SELECT
                d.id,
                d.type,
                d.title,
                d.owner_name,
                d.structured,
                COALESCE(emb_global.vector <=> (SELECT v_global FROM cv_emb), 1.0) AS dist_global,
                COALESCE(emb_skills_tech.vector <=> (SELECT v_skills_tech FROM cv_emb), 1.0) AS dist_skills,
                COALESCE(emb_skills_lang.vector <=> (SELECT v_skills_lang FROM cv_emb), 1.0) AS dist_lang,
                (
                    :w_global * COALESCE(emb_global.vector <=> (SELECT v_global FROM cv_emb), 1.0) +
                    :w_skills * COALESCE(emb_skills_tech.vector <=> (SELECT v_skills_tech FROM cv_emb), 1.0) +
                    :w_lang * COALESCE(emb_skills_lang.vector <=> (SELECT v_skills_lang FROM cv_emb), 1.0)
                ) AS base_score
            FROM documents d
            JOIN document_embeddings emb_global
                ON emb_global.document_id = d.id AND emb_global.kind = 'global'
            JOIN document_embeddings emb_skills_tech
                ON emb_skills_tech.document_id = d.id AND emb_skills_tech.kind = 'skills_tech'
            JOIN document_embeddings emb_skills_lang
                ON emb_skills_lang.document_id = d.id AND emb_skills_lang.kind = 'skills_language'
            WHERE {filter_conditions}
              AND emb_global.vector IS NOT NULL
              AND emb_skills_tech.vector IS NOT NULL
              AND emb_skills_lang.vector IS NOT NULL
        )
        SELECT 
            *,
            CASE 
                WHEN base_score < 0.3 THEN base_score * 0.95
                WHEN base_score < 0.5 THEN base_score * 0.98
                ELSE base_score
            END AS final_score
        FROM scored_matches
        ORDER BY final_score ASC
        LIMIT :limit;
    """)

    rows = db.execute(sql, {
        "cv_id": cv_id,
        "limit": limit * 2,  # Fetch more for re-ranking after symbolic scoring
        "w_global": w_global,
        "w_skills": w_skills,
        "w_lang": w_lang
    }).fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        jd_structured = row.structured or {}

        # Calculate symbolic score for exact requirement matching
        # For CV-to-JD matching, we check if the JD requirements match what CV offers
        symbolic_result = calculate_symbolic_score(jd_structured, cv_data)

        # Get semantic distance (base_score is weighted semantic distance)
        semantic_distance = float(row.base_score) if row.base_score is not None else 1.0

        # Combine semantic and symbolic scores (50/50 by default)
        hybrid_score = combine_semantic_and_symbolic_scores(
            semantic_distance=semantic_distance,
            symbolic_result=symbolic_result,
            semantic_weight=0.5,
            symbolic_weight=0.5
        )

        results.append({
            "id": row.id,
            "title": row.title,
            "owner_name": row.owner_name,
            "structured": jd_structured,
            "dist_global": float(row.dist_global) if row.dist_global is not None else 1.0,
            "dist_skills": float(row.dist_skills) if row.dist_skills is not None else 1.0,
            "dist_lang": float(row.dist_lang) if row.dist_lang is not None else 1.0,
            "base_score": semantic_distance,
            "symbolic_score": symbolic_result,
            "final_score": hybrid_score,
            "weights_used": final_weights
        })

    # Re-sort by hybrid score and limit results
    results.sort(key=lambda x: x["final_score"])
    return results[:limit]


def jd_to_cv_matches(
    db: Session,
    jd_id: int,
    filters: Optional[Dict[str, Any]] = None,
    weights: Optional[Dict[str, float]] = None,
    limit: int = 10,
    use_adaptive_weights: bool = True
) -> List[Dict[str, Any]]:
    """
    Find best matching CVs for a given JD using optimized vector similarity with adaptive weighting.
    """
    cfg_default = settings.matching.weights
    default_weights = {"global": cfg_default.global_, "skills_tech": cfg_default.skills_tech, "skills_language": cfg_default.skills_language}

    # First, verify that the source JD has embeddings
    embedding_check = db.execute(
        text("""
            SELECT kind, CASE WHEN vector IS NOT NULL THEN true ELSE false END as has_vector
            FROM document_embeddings 
            WHERE document_id = :jd_id
        """),
        {"jd_id": jd_id}
    ).fetchall()

    if not embedding_check:
        print(f"Warning: JD {jd_id} has no embeddings stored in database")
        return []

    embedding_status = {row.kind: row.has_vector for row in embedding_check}
    required_kinds = ["global", "skills_tech", "skills_language"]
    missing_kinds = [k for k in required_kinds if k not in embedding_status or not embedding_status.get(k)]

    if missing_kinds:
        print(f"Warning: JD {jd_id} is missing embeddings for: {missing_kinds}")
        return []

    # Get JD data for adaptive weighting
    jd_data = {}
    if use_adaptive_weights:
        try:
            jd_result = db.execute(
                text("SELECT structured FROM documents WHERE id = :jd_id"),
                {"jd_id": jd_id}
            ).fetchone()
            if jd_result:
                jd_data = jd_result.structured
        except Exception as e:
            print(f"Warning: Could not retrieve JD data for adaptive weighting: {e}")

    # Calculate weights with robust validation
    if weights and isinstance(weights, dict) and all(key in weights for key in ["global", "skills_tech", "skills_language"]):
        final_weights = weights
    elif use_adaptive_weights and jd_data:
        try:
            calculated_weights = calculate_adaptive_weights(jd_data, "jd")
            if isinstance(calculated_weights, dict) and all(key in calculated_weights for key in ["global", "skills_tech", "skills_language"]):
                final_weights = calculated_weights
            else:
                print("Warning: Invalid weights returned from calculate_adaptive_weights, using defaults")
                final_weights = default_weights
        except Exception as e:
            print(f"Warning: Error calculating adaptive weights: {e}")
            final_weights = default_weights
    else:
        final_weights = default_weights

    # Extract weights with additional safety checks
    w_global = final_weights.get("global", 0.3)
    w_skills = final_weights.get("skills_tech", 0.5)
    w_lang = final_weights.get("skills_language", 0.2)

    filter_conditions = build_enhanced_filter_conditions(filters, "cv")

    sql = text(f"""
        WITH jd_emb AS (
            SELECT
                (SELECT vector FROM document_embeddings WHERE document_id = :jd_id AND kind = 'global') AS v_global,
                (SELECT vector FROM document_embeddings WHERE document_id = :jd_id AND kind = 'skills_tech') AS v_skills_tech,
                (SELECT vector FROM document_embeddings WHERE document_id = :jd_id AND kind = 'skills_language') AS v_skills_lang
        ),
        scored_matches AS (
            SELECT
                d.id,
                d.type,
                d.title,
                d.owner_name,
                d.structured,
                COALESCE(emb_global.vector <=> (SELECT v_global FROM jd_emb), 1.0) AS dist_global,
                COALESCE(emb_skills_tech.vector <=> (SELECT v_skills_tech FROM jd_emb), 1.0) AS dist_skills,
                COALESCE(emb_skills_lang.vector <=> (SELECT v_skills_lang FROM jd_emb), 1.0) AS dist_lang,
                (
                    :w_global * COALESCE(emb_global.vector <=> (SELECT v_global FROM jd_emb), 1.0) +
                    :w_skills * COALESCE(emb_skills_tech.vector <=> (SELECT v_skills_tech FROM jd_emb), 1.0) +
                    :w_lang * COALESCE(emb_skills_lang.vector <=> (SELECT v_skills_lang FROM jd_emb), 1.0)
                ) AS base_score
            FROM documents d
            JOIN document_embeddings emb_global
                ON emb_global.document_id = d.id AND emb_global.kind = 'global'
            JOIN document_embeddings emb_skills_tech
                ON emb_skills_tech.document_id = d.id AND emb_skills_tech.kind = 'skills_tech'
            JOIN document_embeddings emb_skills_lang
                ON emb_skills_lang.document_id = d.id AND emb_skills_lang.kind = 'skills_language'
            WHERE {filter_conditions}
              AND emb_global.vector IS NOT NULL
              AND emb_skills_tech.vector IS NOT NULL
              AND emb_skills_lang.vector IS NOT NULL
        )
        SELECT 
            *,
            CASE 
                WHEN base_score < 0.3 THEN base_score * 0.95
                WHEN base_score < 0.5 THEN base_score * 0.98
                ELSE base_score
            END AS final_score
        FROM scored_matches
        ORDER BY final_score ASC
        LIMIT :limit;
    """)

    rows = db.execute(sql, {
        "jd_id": jd_id,
        "limit": limit * 2,  # Fetch more for re-ranking after symbolic scoring
        "w_global": w_global,
        "w_skills": w_skills,
        "w_lang": w_lang
    }).fetchall()

    results: List[Dict[str, Any]] = []
    for row in rows:
        cv_structured = row.structured or {}

        # Calculate symbolic score for exact requirement matching
        symbolic_result = calculate_symbolic_score(jd_data, cv_structured)

        # Get semantic distance (base_score is weighted semantic distance)
        semantic_distance = float(row.base_score) if row.base_score is not None else 1.0

        # Combine semantic and symbolic scores (50/50 by default)
        # This hybrid approach ensures:
        # - Semantic: captures overall context and implicit matches
        # - Symbolic: ensures exact requirement fulfillment (languages, skills, experience)
        hybrid_score = combine_semantic_and_symbolic_scores(
            semantic_distance=semantic_distance,
            symbolic_result=symbolic_result,
            semantic_weight=0.5,
            symbolic_weight=0.5
        )

        results.append({
            "id": row.id,
            "title": row.title,
            "owner_name": row.owner_name,
            "structured": cv_structured,
            "dist_global": float(row.dist_global) if row.dist_global is not None else 1.0,
            "dist_skills": float(row.dist_skills) if row.dist_skills is not None else 1.0,
            "dist_lang": float(row.dist_lang) if row.dist_lang is not None else 1.0,
            "base_score": semantic_distance,
            "symbolic_score": symbolic_result,
            "final_score": hybrid_score,
            "weights_used": final_weights
        })

    # Re-sort by hybrid score and limit results
    results.sort(key=lambda x: x["final_score"])
    return results[:limit]


def bulk_match_optimization(
    db: Session,
    document_ids: List[int],
    target_type: str,
    batch_size: int = 50
) -> Dict[int, List[Dict[str, Any]]]:
    """
    Optimize bulk matching operations by batching and caching common embeddings.
    """
    results = {}

    for i in range(0, len(document_ids), batch_size):
        batch = document_ids[i:i + batch_size]

        for doc_id in batch:
            if target_type == "cv":
                matches = cv_to_jd_matches(db, doc_id, limit=5, use_adaptive_weights=True)
            else:
                matches = jd_to_cv_matches(db, doc_id, limit=5, use_adaptive_weights=True)

            results[doc_id] = matches

    return results
