import sqlalchemy as sa


from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship


class Workflow(SQLModel, table=True):
    """
    Model to represent a shared Workflow identification between
    Accession Jobs and Verification Jobs.

      id: Optional is declared only for Python's needs before a db object is
          created. This field cannot be null in the database.
    """

    __tablename__ = "workflow"

    id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, primary_key=True))
    update_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    create_dt: datetime = Field(
        sa_column=sa.Column(sa.TIMESTAMP(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    )
    accession_job: Optional["AccessionJob"] = Relationship(back_populates="workflow")
    verification_job: Optional["VerificationJob"] = Relationship(
        back_populates="workflow"
    )
    verification_change: Optional["VerificationChange"] = Relationship(
        back_populates="workflow"
    )
