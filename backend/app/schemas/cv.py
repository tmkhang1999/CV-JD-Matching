from pydantic import BaseModel
from typing import List, Optional, Dict


class RawSection(BaseModel):
    section_title: Optional[str] = None
    content: Optional[str] = None


class Contact(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    links: List[str] = []


class Identity(BaseModel):
    full_name: Optional[str] = None
    location: Optional[str] = None
    contact: Optional[Contact] = None


class Headline(BaseModel):
    current_position: Optional[str] = None
    seniority: Optional[str] = None
    total_years_of_experience: Optional[float] = None


class SkillItem(BaseModel):
    name: str
    years_used: Optional[float] = None
    last_used_year: Optional[int] = None
    proficiency: Optional[str] = None


class SkillGroup(BaseModel):
    programming_languages: List[SkillItem] = []
    frameworks: List[SkillItem] = []
    databases: List[SkillItem] = []
    cloud_platforms: List[SkillItem] = []
    tools_platforms: List[SkillItem] = []
    methodologies: List[str] = []


class Project(BaseModel):
    project_name: Optional[str] = None
    domain: List[str] = []
    role: Optional[str] = None
    team_size: Optional[str] = None
    description: Optional[str] = None
    responsibilities: List[str] = []
    technologies: List[str] = []
    impacts_contributions: List[str] = []


class ExperienceItem(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    location: Optional[str] = None
    highlights: List[str] = []
    projects: List[Project] = []


class EducationItem(BaseModel):
    school: Optional[str] = None
    degree: Optional[str] = None
    major: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None


class CertificationItem(BaseModel):
    name: Optional[str] = None
    issuer: Optional[str] = None
    year: Optional[int] = None
    credential_url: Optional[str] = None


class LanguageItem(BaseModel):
    name: Optional[str] = None
    level: Optional[str] = None
    test: Optional[Dict[str, Optional[str]]] = None


class CandidateProfile(BaseModel):
    identity: Identity
    headline: Optional[Headline] = None
    summary: Optional[str] = None
    skills: SkillGroup
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    certifications: List[CertificationItem] = []
    languages: List[LanguageItem] = []
    domain_expertise: List[str] = []
    awards_achievements: List[str] = []
    activities: List[str] = []
    raw_sections: List[RawSection] = []


class CVStructured(BaseModel):
    candidate_profile: CandidateProfile


class CVCreateResponse(BaseModel):
    id: int
    cv_id: Optional[str] = None
    structured: CVStructured
