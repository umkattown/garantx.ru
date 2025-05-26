# models.py

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Post(Base):
    __tablename__ = "posts"

    id = sa.Column(sa.Integer, primary_key=True, index=True)
    category = sa.Column(sa.String, index=True)
    content = sa.Column(sa.Text)

    def __repr__(self):
        return f"<Post(id={self.id}, category='{self.category}')>"
