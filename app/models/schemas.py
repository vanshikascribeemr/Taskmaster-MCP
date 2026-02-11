from pydantic import BaseModel, Field
from typing import List, Optional

class Task(BaseModel):
    taskId: int = Field(alias="TaskId")
    taskSubject: str = Field(alias="SubjectLine")
    taskStatus: str = Field(alias="LastStatusCode")
    taskPriority: str = Field(alias="TaskPriority")
    assigneeName: Optional[str] = Field(None, alias="TaskAssignedtoName")
    followUpComments: List[str] = Field(default_factory=list)
    daysOverdue: Optional[int] = Field(0, alias="DaysOverdue")
    importanceScore: float = 0.0

    class Config:
        populate_by_name = True

class CategoryData(BaseModel):
    categoryId: int
    categoryName: str
    tasks: List[Task] = Field(default_factory=list)

class CategoryBrief(BaseModel):
    id: int
    name: str

class UserSubscription(BaseModel):
    user_email: str
    category_id: int

class NewsletterPreview(BaseModel):
    category_name: str
    summary: str
    tasks: List[dict]

