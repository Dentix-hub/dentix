from pydantic import BaseModel
from typing import List, Optional


class OnboardingSubStep(BaseModel):
    key: str
    title: str
    done: bool


class OnboardingStep(BaseModel):
    id: str
    key: str
    title: str
    description: str
    link: str
    done: bool
    highlight: bool = False
    sub_steps: Optional[List[OnboardingSubStep]] = None


class OnboardingSection(BaseModel):
    id: str
    title: str
    steps: List[OnboardingStep]


class OnboardingProgress(BaseModel):
    total: int
    completed: int
    percentage: int


class OnboardingStatusResponse(BaseModel):
    enabled: bool
    role: Optional[str] = None
    dismissed: bool = False
    seen_tips: List[str] = []
    progress: OnboardingProgress
    sections: List[OnboardingSection] = []
    steps: List[OnboardingStep] = []


class OnboardingEventRequest(BaseModel):
    event_key: str


class OnboardingDismissRequest(BaseModel):
    dismissed: bool = True
