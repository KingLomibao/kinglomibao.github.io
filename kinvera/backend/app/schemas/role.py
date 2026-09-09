from pydantic import BaseModel

from app.models import Role


class RoleSchema(BaseModel):
    id: int
    code: str
    name: str
    category: str

    @classmethod
    def from_orm_role(cls, role: Role) -> "RoleSchema":
        return cls(id=role.id, code=role.code, name=role.name, category=role.category.value)
