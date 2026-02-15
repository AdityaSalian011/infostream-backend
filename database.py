# ============================================
# DATABASE CONNECTION CONFIGURATION
# ============================================
# This file sets up the connection to your MySQL database
# SQLAlchemy is an ORM (Object-Relational Mapping) tool that lets you
# work with databases using Python objects instead of raw SQL queries

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# ============================================
# DATABASE URL CONFIGURATION
# ============================================
# Railway provides DATABASE_URL automatically
# Local development uses the fallback URL

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://root:root@localhost:3306/infostreamdigest'
)

# ============================================
# FIX RAILWAY MySQL URL FORMAT
# ============================================
# Railway provides mysql:// but SQLAlchemy+PyMySQL needs mysql+pymysql://
if DATABASE_URL.startswith('mysql://'):
    DATABASE_URL = DATABASE_URL.replace('mysql://', 'mysql+pymysql://', 1)

# ============================================
# CREATE DATABASE ENGINE
# ============================================
# The engine is the starting point for any SQLAlchemy application
# It manages connections to the database
# 
# Parameters explained:
# - echo=True: Prints all SQL queries to console (helpful for debugging, set to False in production)
# - pool_pre_ping=True: Tests connections before using them (prevents "MySQL has gone away" errors)
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# ============================================
# CREATE SESSION FACTORY
# ============================================
# Sessions are used to interact with the database
# Think of a session as a "conversation" with the database
# 
# Parameters explained:
# - autocommit=False: Changes aren't saved automatically (you control when to save)
# - autoflush=False: Changes aren't sent to DB automatically (you control when to send)
# - bind=engine: Links this session factory to our database engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ============================================
# CREATE BASE CLASS FOR MODELS
# ============================================
# All your database models (like UserDetail) will inherit from this Base class
# This is how SQLAlchemy knows which classes represent database tables

Base = declarative_base()

# ============================================
# DEPENDENCY FUNCTION FOR FASTAPI
# ============================================
# This function provides a database session to your API endpoints
# It automatically closes the session when the request is done
# Use this in your FastAPI route functions with Depends()

def get_db():
    """
    Creates a new database session for each request.
    Automatically closes the session when the request completes.
    
    Usage in FastAPI:
        @app.post('/endpoint')
        def my_endpoint(db: Session = Depends(get_db)):
            # Use db here to query/add data
            pass
    """
    db = SessionLocal()  # Creates a new session
    try:
        yield db  # Provide the session to the route function
    finally:
        db.close()  # Always close the session when done