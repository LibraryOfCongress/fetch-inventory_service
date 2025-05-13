import sqlalchemy as sa


from typing import Optional, List
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship


class ContainerType(SQLModel, table=True):
    """
    Model to represent container types.

    Container Types have owners.
    Container Types are tracked on shelves for types a Shelf accepts.
    Container Types are tracked on trays for container type it is.
    Container Types are tracked on items and the value is inherited from the tray.

    Container Types are tracked on non-trays(non-trayed-items), and the value is not inherited.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "container_types"

    id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, primary_key=True), default=None)
    type: str = Field(sa_column=sa.Column(sa.VARCHAR(25), nullable=False, unique=True))
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )

    # shelves assigned this container type
    shelves: List["Shelf"] = Relationship(back_populates="container_type")
    # accession jobs for this container type
    accession_jobs: List["AccessionJob"] = Relationship(back_populates="container_type")
    verification_jobs: List["VerificationJob"] = Relationship(
        back_populates="container_type"
    )
    move_discrepancies: List["MoveDiscrepancy"] = Relationship(
        back_populates="container_type",
        sa_relationship_kwargs={
            "primaryjoin": "MoveDiscrepancy.container_type_id==ContainerType.id",
            "lazy": "selectin"
        }
    )
