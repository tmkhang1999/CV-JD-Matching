from typing import List, Optional
from pydantic import BaseModel


class RawSection(BaseModel):
    section_title: Optional[str] = None
    content: Optional[str] = None


class Client(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None


class Employment(BaseModel):
    type: Optional[str] = None
    working_mode: Optional[str] = None
    location: Optional[str] = None
    work_hours: Optional[str] = None
    remote_policy: Optional[str] = None


class Experience(BaseModel):
    min_years: Optional[float] = None
    seniority_notes: Optional[str] = None


class LanguageRequirement(BaseModel):
    name: Optional[str] = None
    level: Optional[str] = None
    test: Optional[dict] = None


class RequirementItem(BaseModel):
    category: Optional[str] = None
    items: List[str] = []


class Requirements(BaseModel):
    must_have: List[RequirementItem] = []
    nice_to_have: List[RequirementItem] = []
    education: List[str] = []
    languages: List[LanguageRequirement] = []


class Skills(BaseModel):
    backend: List[str] = []
    frontend: List[str] = []
    mobile: List[str] = []
    database: List[str] = []
    cloud_devops: List[str] = []
    data_ml: List[str] = []
    qa: List[str] = []
    security: List[str] = []
    architecture: List[str] = []
    methodologies: List[str] = []
    tools: List[str] = []


class CompensationBenefits(BaseModel):
    salary_range: Optional[str] = None
    bonus: Optional[str] = None
    allowances: List[str] = []
    insurance: List[str] = []
    pto: Optional[str] = None
    other_benefits: List[str] = []


class Process(BaseModel):
    interview_steps: List[str] = []
    start_date: Optional[str] = None


class JobProfile(BaseModel):
    title: Optional[str] = None
    level: Optional[str] = None
    domain: List[str] = []
    client: Optional[Client] = None
    employment: Optional[Employment] = None
    experience: Optional[Experience] = None
    responsibilities: List[str] = []
    requirements: Requirements
    skills: Skills
    compensation_benefits: Optional[CompensationBenefits] = None
    process: Optional[Process] = None
    raw_sections: List[RawSection] = []


class JDStructured(BaseModel):
    job_profile: JobProfile


class JDCreateResponse(BaseModel):
    id: int
    jd_id: Optional[str] = None
    structured: JDStructured
