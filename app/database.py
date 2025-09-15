import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

data_dir = "data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

SQLALCHEMY_DATABASE_URL = f"sqlite:///./{data_dir}/links.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()