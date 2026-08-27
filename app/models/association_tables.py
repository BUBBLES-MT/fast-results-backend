from sqlalchemy import Table, Column, Integer, ForeignKey
from app.core.database import Base

# Teacher - Class association table
teacher_classes = Table(
    "teacher_classes",
    Base.metadata,
    Column("teacher_id", Integer, ForeignKey("teachers.id", ondelete="CASCADE")),
    Column("class_id", Integer, ForeignKey("classes.id", ondelete="CASCADE"))
)