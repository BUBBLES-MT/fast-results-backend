from pydantic import BaseModel, EmailStr, constr

# Schema ya ku-create SuperAdmin
class SuperAdminCreate(BaseModel):
    name: constr(min_length=3, max_length=100)
    username: constr(min_length=3, max_length=50)
    email: EmailStr
    password: constr(min_length=6)

# Schema ya response
class SuperAdminResponse(BaseModel):
    id: int
    name: str
    username: str
    email: EmailStr
    is_active: bool = True

    class Config:
        orm_mode = True