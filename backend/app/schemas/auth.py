from pydantic import BaseModel, EmailStr


class GoogleLogin(BaseModel):
    credential: str


class DevLogin(BaseModel):
    email: EmailStr = "demo@example.com"
    name: str = "Demo User"


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    picture: str | None
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

