from sqlmodel import Field, SQLModel


class OwnersSizeClassesLink(SQLModel, table=True):
    __tablename__ = "owners_size_classes"
    owner_id: int | None = Field(
        default=None, foreign_key="owners.id", primary_key=True
    )
    size_class_id: int | None = Field(
        default=None, foreign_key="size_class.id", primary_key=True
    )
