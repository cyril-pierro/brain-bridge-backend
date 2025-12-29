from pydantic import BaseModel, model_validator, computed_field
from uuid import UUID
from typing import List


class TeamUserOut(BaseModel):
    id: UUID
    full_name: str

    @model_validator(mode="before")
    def format_full_name(cls, data):
        if isinstance(data, dict):
            data["full_name"] = data["full_name"].replace("-", " ")
            return data
        data.full_name = data.full_name.replace("-", " ")
        return data

    class Config:
        from_attributes = True


class TeamJoinRequestOut(BaseModel):
    id: int
    user: TeamUserOut

    class Config:
        from_attributes = True


class TeamIn(BaseModel):
    name: str


class TeamOut(BaseModel):
    id: int
    name: str
    code: str
    creator:  TeamUserOut
    students: list[TeamUserOut] = []
    pending_requests: list[TeamJoinRequestOut] = []

    @computed_field
    @property
    def members(self) -> List[TeamUserOut]:
        """All team members including creator and students"""
        members = [self.creator] if self.creator else []
        members.extend(self.students)
        return members

    class Config:
        from_attributes = True
