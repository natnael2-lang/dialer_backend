from pydantic import BaseModel, Field, field_validator


def _clean(v: str) -> str:
    return " ".join(v.split())


class ProfileOut(BaseModel):
    chatid: str
    name: str
    bio: str
    photo_url: str | None = None


class RegisterOut(BaseModel):
    profile: ProfileOut
    token: str


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    bio: str | None = Field(default=None, max_length=280)

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        if v is None:
            return v
        v = _clean(v)
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class ContactCreate(BaseModel):
    chatid: str = Field(min_length=3, max_length=16, pattern=r"^\d+$")
    nickname: str | None = Field(default=None, max_length=80)


class ContactUpdate(BaseModel):
    nickname: str = Field(min_length=1, max_length=80)

    @field_validator("nickname")
    @classmethod
    def _nick(cls, v):
        v = _clean(v)
        if not v:
            raise ValueError("Name cannot be empty")
        return v


class ContactOut(BaseModel):
    id: int
    nickname: str
    profile: ProfileOut