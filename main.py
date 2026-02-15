from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from hashlib import sha256

# Import database components
from database import engine, Base, get_db
from models import UserDetail, UserSetting, NewsTopicAndScheduleTime

# Import NewsApi, WeatherAPI and StockAPI
from news.news import NewsAPI
from weather.weather import WeatherAPI
from stock.stock import StockAPI

# Scheduling task modules
from contextlib import asynccontextmanager
from scheduler import start_scheduler, stop_scheduler, scheduler

import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Replaces deprecated @app.on_event('startup') and @app.on_event('shutdown')
    """
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()

app = FastAPI(lifespan=lifespan)

# ============================================
# PASSWORD HASHING CONFIGURATION
# ============================================
pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

def hash_password(password: str) -> str:
    """Hash a password using bcrypt with SHA-256 pre-hashing"""
    sha256_hash = sha256(password.encode('utf-8')).hexdigest()
    return pwd_context.hash(sha256_hash)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    sha256_hash = sha256(plain_password.encode('utf-8')).hexdigest()
    return pwd_context.verify(sha256_hash, hashed_password)

# ============================================
# CORS CONFIGURATION
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://127.0.0.1:5500',
        "http://localhost:5500",
        "https://infostream-frontend.vercel.app",
        os.getenv(
            'FRONTEND_URL',
        )
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

# ============================================
# CREATE DATABASE TABLES
# ============================================
Base.metadata.create_all(bind=engine)

# ============================================
# PYDANTIC SCHEMAS
# ============================================

# User Authentication Schemas
class UserSignUpRequest(BaseModel):
    firstName: str
    lastName: str
    fullName: Optional[str] = None
    email: EmailStr
    password: str

    class Config:
        from_attributes = True

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    firstName: str
    lastName: str
    fullName: str
    email: str

    class Config:
        from_attributes = True

# User Settings Schemas
class UserSettingRequest(BaseModel):
    country: Optional[str] = None
    city: Optional[str] = None
    newsApi: Optional[str] = None
    weatherApi: Optional[str] = None

class UserSettingResponse(BaseModel):
    id: int = Field(alias='setting_id')  # Map database setting_id to response id
    user_id: int
    country: str
    city: str
    # Note: Not returning API keys for security

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow both field names

# News Topic and Schedule Schemas
class NewsTopicScheduleRequest(BaseModel):
    newsTopic: Optional[str] = None
    isCustomTopic: Optional[bool] = None
    deliveryTime: Optional[str] = None
    isImmediate: Optional[bool] = None
    isScheduled: Optional[bool] = None

class NewsTopicScheduleResponse(BaseModel):
    id: int = Field(alias='news_id')  # Map database news_id to response id
    user_id: int
    newsTopic: str
    isCustomTopic: bool
    deliveryTime: str
    isImmediate: bool
    isScheduled: bool

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow both field names

# ============================================
# ROOT ENDPOINT
# ============================================
@app.get('/')
async def root():
    """API documentation and available endpoints"""
    return {
        "message": "InfoStream Digest API",
        "version": "2.0",
        "endpoints": {
            "authentication": {
                "signup": "POST /signup",
                "login": "POST /login"
            },
            "user_settings": {
                "create": "POST /settings/{user_id}",
                "get": "GET /settings/{user_id}",
                "update": "PUT /settings/{user_id}",
                "delete": "DELETE /settings/{user_id}"
            },
            "news_preferences": {
                "create": "POST /news-preferences/{user_id}",
                "get": "GET /news-preferences/{user_id}",
                "update": "PUT /news-preferences/{preference_id}",
                "delete": "DELETE /news-preferences/{preference_id}"
            }
        }
    }

# ============================================
# AUTHENTICATION ENDPOINTS
# ============================================

@app.post('/signup', response_model=UserResponse)
async def signup_user(user_data: UserSignUpRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.
    - Checks if email already exists
    - Hashes password before storing
    - Returns user info (without password)
    """
    try:
        # Check if email already exists
        existing_user = db.query(UserDetail).filter(
            UserDetail.email == user_data.email
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail='Email already registered. Please login or use a different email.'
            )

        # Hash the password
        hashed_password = hash_password(user_data.password)

        # Create new user
        new_user = UserDetail(
            firstName=user_data.firstName,
            lastName=user_data.lastName,
            fullName=user_data.fullName or f'{user_data.firstName} {user_data.lastName}',
            email=user_data.email,
            password=hashed_password
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return new_user

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error during signup: {str(exc)}'
        )

@app.post('/login')
async def login_user(login_data: UserLoginRequest, db: Session = Depends(get_db)):
    """
    Login user and determine redirect based on profile completion.
    
    Flow:
    1. Verify credentials
    2. Check if user has completed settings
    3. Check if user has completed news preferences
    4. Return redirect URL based on completion status
    """
    try:
        # Find user by email
        user = db.query(UserDetail).filter(
            UserDetail.email == login_data.email
        ).first()

        if not user:
            raise HTTPException(
                status_code=401,
                detail='Invalid email or password'
            )

        # Verify password
        if not verify_password(login_data.password, user.password):
            raise HTTPException(
                status_code=401,
                detail='Invalid email or password'
            )

        # Check profile completion status
        user_settings = db.query(UserSetting).filter(
            UserSetting.user_id == user.id
        ).first()

        news_preferences = db.query(NewsTopicAndScheduleTime).filter(
            NewsTopicAndScheduleTime.user_id == user.id
        ).first()

        # Determine redirect URL
        if not user_settings:
            redirect_url = 'user-settings.html'
        elif not news_preferences:
            redirect_url = 'topic-and-schedule.html'
        else:
            redirect_url = 'news-summary.html'

        return {
            "message": "Login successful",
            "redirect_url": redirect_url,
            "user": {
                "id": user.id,
                "firstName": user.firstName,
                "lastName": user.lastName,
                "fullName": user.fullName,
                "email": user.email
            }
        }

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error during login: {str(exc)}'
        )

# ============================================
# USER SETTINGS ENDPOINTS (Page 2)
# ============================================

@app.post('/settings/{user_id}', response_model=UserSettingResponse)
async def create_user_settings(
    user_id: int,
    settings_data: UserSettingRequest,
    db: Session = Depends(get_db)
):
    """
    Create user settings (country, city, API keys).
    Called when user completes the settings page.
    """
    try:
        # Verify user exists
        user = db.query(UserDetail).filter(UserDetail.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        # Check if settings already exist
        existing_settings = db.query(UserSetting).filter(
            UserSetting.user_id == user_id
        ).first()

        if existing_settings:
            raise HTTPException(
                status_code=400,
                detail='Settings already exist. Use PUT /settings/{user_id} to update.'
            )

        # Validate required fields
        if not settings_data.country or not settings_data.city:
            raise HTTPException(
                status_code=400,
                detail='Country and city are required'
            )

        # Create new settings
        new_settings = UserSetting(
            user_id=user_id,
            country=settings_data.country,
            city=settings_data.city,
            newsApi=settings_data.newsApi,
            weatherApi=settings_data.weatherApi
        )

        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)

        return new_settings

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error creating settings: {str(exc)}'
        )

@app.put('/settings/{user_id}', response_model=UserSettingResponse)
async def update_user_settings(
    user_id: int,
    settings_data: UserSettingRequest,
    db: Session = Depends(get_db)
):
    """
    Update user settings (partial update supported).
    Only updates fields that are provided in the request.
    """
    try:
        settings = db.query(UserSetting).filter(
            UserSetting.user_id == user_id
        ).first()

        if not settings:
            raise HTTPException(
                status_code=404,
                detail='Settings not found. Use POST /settings/{user_id} to create.'
            )

        # Update only provided fields
        update_data = settings_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(settings, field, value)

        db.commit()
        db.refresh(settings)

        return settings

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error updating settings: {str(exc)}'
        )
# ============================================
# NEWS PREFERENCES ENDPOINTS (Page 3)
# ============================================

@app.post('/news-preferences/{user_id}', response_model=NewsTopicScheduleResponse)
async def create_news_preferences(
    user_id: int,
    preference_data: NewsTopicScheduleRequest,
    db: Session = Depends(get_db)
):
    """
    Create news preferences (topic and schedule).
    Called when user completes the news preferences page.
    """
    try:
        # Verify user exists
        user = db.query(UserDetail).filter(UserDetail.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail='User not found')

        # Validate required fields
        if not preference_data.newsTopic:
            raise HTTPException(
                status_code=400,
                detail='News topic is required'
            )
        
        if not preference_data.deliveryTime:
            raise HTTPException(
                status_code=400,
                detail='Delivery time is required'
            )

        # Create new preferences
        new_preferences = NewsTopicAndScheduleTime(
            user_id=user_id,
            newsTopic=preference_data.newsTopic,
            isCustomTopic=preference_data.isCustomTopic or False,
            deliveryTime=preference_data.deliveryTime,
            isImmediate=preference_data.isImmediate or False,
            isScheduled=preference_data.isScheduled or False
        )

        db.add(new_preferences)
        db.commit()
        db.refresh(new_preferences)

        return new_preferences

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error creating news preferences: {str(exc)}'
        )

@app.get('/news-preferences/{user_id}')
async def get_news_preferences(user_id: int, db: Session = Depends(get_db)):
    """
    Get all news preferences for a user.
    Returns a list since a user can have multiple preferences.
    """
    try:
        preferences = db.query(NewsTopicAndScheduleTime).filter(
            NewsTopicAndScheduleTime.user_id == user_id
        ).all()

        if not preferences:
            return {
                "message": "No preferences found for this user",
                "preferences": []
            }

        return {
            "user_id": user_id,
            "preferences": [
                {
                    "id": pref.news_id,  # Fixed: use news_id instead of id
                    "newsTopic": pref.newsTopic,
                    "isCustomTopic": pref.isCustomTopic,
                    "deliveryTime": pref.deliveryTime,
                    "isImmediate": pref.isImmediate,
                    "isScheduled": pref.isScheduled
                }
                for pref in preferences
            ]
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f'Error fetching preferences: {str(exc)}'
        )

@app.put('/news-preferences/{preference_id}', response_model=NewsTopicScheduleResponse)
async def update_news_preferences(
    preference_id: int,
    preference_data: NewsTopicScheduleRequest,
    db: Session = Depends(get_db)
):
    """
    Update specific news preference by its ID.
    Supports partial updates.
    """
    try:
        preference = db.query(NewsTopicAndScheduleTime).filter(
            NewsTopicAndScheduleTime.news_id == preference_id  # Fixed: use news_id instead of id
        ).first()

        if not preference:
            raise HTTPException(
                status_code=404,
                detail='Preference not found'
            )

        # Update only provided fields
        update_data = preference_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(preference, field, value)

        db.commit()
        db.refresh(preference)

        return preference

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error updating preference: {str(exc)}'
        )

@app.delete('/news-preferences/{preference_id}')
async def delete_news_preference(preference_id: int, db: Session = Depends(get_db)):
    """Delete a specific news preference"""
    try:
        preference = db.query(NewsTopicAndScheduleTime).filter(
            NewsTopicAndScheduleTime.news_id == preference_id  # Fixed: use news_id instead of id
        ).first()

        if not preference:
            raise HTTPException(status_code=404, detail='Preference not found')

        deleted_info = {
            "id": preference.news_id,  # Fixed: use news_id instead of id
            "user_id": preference.user_id,
            "newsTopic": preference.newsTopic,
            "deliveryTime": preference.deliveryTime
        }

        db.delete(preference)
        db.commit()

        return {
            "message": "Preference deleted successfully",
            "deleted_preference": deleted_info
        }

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error deleting preference: {str(exc)}'
        )

# ============================================
# SCHEDULER LIFECYCLE
# ============================================
@app.get('/health')
async def health_check():
    """Simple health check for monitoring"""
    return{
        'status': 'ok',
        'scheduler_running': scheduler.running
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)