"""Typed result every skill returns, carrying its risk rating back to the process."""

from typing import Literal

from pydantic import BaseModel


class SkillResult(BaseModel):
    skill: str
    risk: str
    status: Literal["done", "refused"]
    result: str


def refused(skill: str, risk: str, reason: str) -> str:
    return SkillResult(skill=skill, risk=risk, status="refused", result=f"Refused: {reason}").model_dump_json()


def done(skill: str, risk: str, result: str) -> str:
    return SkillResult(skill=skill, risk=risk, status="done", result=result).model_dump_json()
