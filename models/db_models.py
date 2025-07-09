# models/db_models.py
from sqlalchemy import Column, Integer, String, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from database.db import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    description = Column(String)          # index kaldırıldı
    short_description = Column(String)    # index kaldırıldı
    permalink = Column(String)
    embedding = Column(LargeBinary)

class Page(Base):
    __tablename__ = "pages"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    slug = Column(String, index=True)
    content = Column(String)


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    slug = Column(String, index=True)
    description = Column(String)

class Post(Base):
    __tablename__ = "posts"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)
    title = Column(String, index=True)
    slug = Column(String, index=True)
    content = Column(String)
    category_id = Column(Integer, ForeignKey("categories.id"))


class MessageLog(Base):
    __tablename__ = "message_logs"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    role = Column(String)
    content = Column(String)
