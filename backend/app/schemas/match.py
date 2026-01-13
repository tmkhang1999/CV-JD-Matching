from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class MatchFilters(BaseModel):
    """Filters for matching requests"""
    min_years: Optional[int] = None
    max_years: Optional[int] = None
    required_skills: Optional[List[str]] = None
    domains: Optional[List[str]] = None
    seniority: Optional[List[str]] = None
    role_categories: Optional[List[str]] = None


class MatchWeights(BaseModel):
    """Weights for different similarity components"""
    global_: float = Field(0.3, alias="global")
    skills_tech: float = 0.5
    skills_language: float = 0.2


class MatchRequest(BaseModel):
    """Request for matching documents"""
    filters: Optional[MatchFilters] = None
    weights: Optional[MatchWeights] = None
    top_k: int = 10


class MatchResult(BaseModel):
    """A single match result"""
    id: int
    title: Optional[str] = "Untitled"
    owner_name: Optional[str] = "Unknown"
    score: float  # Using final_score from matching service (hybrid semantic+symbolic)
    base_score: float  # Pure semantic score
    dist_global: float
    dist_skills: float
    dist_lang: float
    symbolic_score: Optional[Dict[str, Any]] = None  # Detailed symbolic matching breakdown
    structured: Dict[str, Any]
    weights_used: Optional[Dict[str, float]] = None


class MatchResponse(BaseModel):
    """Response containing matching results"""
    source_id: int
    source_type: str
    results: List[MatchResult]


class LLMRerankResult(BaseModel):
    """A single reranked result with LLM analysis"""
    id: int
    title: Optional[str] = "Untitled"
    owner_name: Optional[str] = "Unknown"
    vector_score: int  # 0-100 similarity percentage
    llm_score: int  # 0-100
    final_rank: Optional[int] = None
    explanation: str
    structured: Dict[str, Any]


class LLMRerankResponse(BaseModel):
    """Response containing LLM reranked results"""
    cv_id: Optional[int] = None
    jd_id: Optional[int] = None
    results: List[LLMRerankResult]
