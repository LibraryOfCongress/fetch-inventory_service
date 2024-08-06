import sqlalchemy as sa

from typing import Optional, List
from datetime import datetime
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
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    create_dt: datetime = Field(
        sa_column=sa.DateTime, default=datetime.utcnow(), nullable=False
    )
    accession_job: Optional["AccessionJob"] = Relationship(back_populates="workflow")
    verification_job: Optional["VerificationJob"] = Relationship(back_populates="workflow")
