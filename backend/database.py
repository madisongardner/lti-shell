from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import DeclarativeBase

engine = create_engine('sqlite:///lti_shell.db') # Database engine
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase):   #base class each db model will inherit
    pass


def get_db():           # Dependency injection function to get a database session
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

