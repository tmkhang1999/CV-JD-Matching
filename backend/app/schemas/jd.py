from typing import List, Optional
from pydantic import BaseModel, Field


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
    items: List[str] = Field(default_factory=list)


class Requirements(BaseModel):
    must_have: List[RequirementItem] = Field(default_factory=list)
    nice_to_have: List[RequirementItem] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    languages: List[LanguageRequirement] = Field(default_factory=list)


class Skills(BaseModel):
    backend: List[str] = Field(default_factory=list)
    frontend: List[str] = Field(default_factory=list)
    mobile: List[str] = Field(default_factory=list)
    database: List[str] = Field(default_factory=list)
    cloud_devops: List[str] = Field(default_factory=list)
    data_ml: List[str] = Field(default_factory=list)
    qa: List[str] = Field(default_factory=list)
    security: List[str] = Field(default_factory=list)
    architecture: List[str] = Field(default_factory=list)
    methodologies: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)


class CompensationBenefits(BaseModel):
    salary_range: Optional[str] = None
    bonus: Optional[str] = None
    allowances: List[str] = Field(default_factory=list)
    insurance: List[str] = Field(default_factory=list)
    pto: Optional[str] = None
    other_benefits: List[str] = Field(default_factory=list)


class Process(BaseModel):
    interview_steps: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None


class JobProfile(BaseModel):
    title: Optional[str] = None
    level: Optional[str] = None
    domain: List[str] = Field(default_factory=list)
    client: Optional[Client] = None
    employment: Optional[Employment] = None
    experience: Optional[Experience] = None
    responsibilities: List[str] = Field(default_factory=list)
    requirements: Requirements
    skills: Skills
    compensation_benefits: Optional[CompensationBenefits] = None
    process: Optional[Process] = None
    raw_sections: List[RawSection] = Field(default_factory=list)


class JDStructured(BaseModel):
    job_profile: JobProfile


class JDCreateResponse(BaseModel):
    id: int
    jd_id: Optional[str] = None
    structured: JDStructured
