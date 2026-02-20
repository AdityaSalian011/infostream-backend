from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from hashlib import sha256

## JWT Dependencies
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer

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
from dotenv import load_dotenv
import logging

load_dotenv()

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

SECRET_KEY = os.getenv('SECRET_KEY', 'FvJ6AYVkzHU0lDetGGNgsOwbxvbw51lve7X2srr1RLd')
ALGORITHM = os.getenv('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '300'))

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a JWT access token
    - data: Dictionary containing user information (typically just user_id)
    - expires_delta: Token expiration time
    """
    to_encode = data.copy()

    if expires_delta:
        expires = datetime.now(timezone.utc) + expires_delta
    else:
        expires = datetime.now(timezone.utc) + timedelta(minutes=60)

    to_encode.update({
        'exp': expires
    })

    encoded_jwt = jwt.encode(to_encode, key=SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
):
    """
    Verify JWT token and return current user from database
    - This is used as a dependency for protected routes
    - Automatically validates token and fetches user data
    """
    credentials_exception = HTTPException(
        status_code=401,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': 'Bearer'}
    )

    try:
        # Decode the jwt token
        payload = jwt.decode(token, key=SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get('sub')

        if not user_id:
            raise credentials_exception
        
        user_id = int(user_id)  ## convert str back to int for db query
    except JWTError:
        raise credentials_exception
    
    # Get the user from database
    user = db.query(UserDetail).filter(
        UserDetail.id == user_id
    ).first()

    if not user:
        raise credentials_exception
    
    return user

# ============================================
# CORS CONFIGURATION
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://127.0.0.1:5500',
        "http://localhost:5500",
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

## Token as a response
class Token(BaseModel):
    access_token: str
    token_type: str

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

@app.post('/signup', response_model=Token)
async def signup_user(user_data: UserSignUpRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.
    - Checks if email already exists
    - Hashes password before storing
    - Returns a JWT token (Not user directly)
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

        # ============================================
        # 🔒 NEW: Create JWT token with only user ID
        # WHY: Token contains minimal data (just user_id) for security
        # Frontend uses this token to fetch user data when needed
        # ============================================
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                'sub': str(new_user.id)
            }, # 'sub' is standard JWT claim for user identifier  
            ## sub should be an str not an int
            expires_delta=access_token_expires
        )

        return {
            'access_token': access_token,
            'token_type': 'bearer' 
        }

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error during signup: {str(exc)}'
        )

@app.post('/login', response_model=Token)
async def login_user(
    login_data: UserLoginRequest, 
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT token.
    Frontend will use this token to:
    1. Call /users/me to get user data
    2. Call /users/me/redirect to determine where to redirect
    """
    try:
        # Step1: Find user by email
        user = db.query(UserDetail).filter(
            UserDetail.email == login_data.email
        ).first()

        if not user:
            raise HTTPException(
                status_code=401,
                detail='Invalid email or password'
            )

        # Step2: Verify password
        if not verify_password(login_data.password, user.password):
            raise HTTPException(
                status_code=401,
                detail='Invalid email or password'
            )

        # Step3: create JWT token with user_id
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={'sub': str(user.id)},  ## userId as str and not int
            expires_delta=access_token_expires
        )

        return{
            'access_token': access_token,
            'token_type': 'bearer'
        }

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error during login: {str(exc)}'
        )

@app.get('/user/redirect')
async def get_redirect_url(
    current_user: UserDetail = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Determine where to redirect user based on profile completion (PROTECTED ROUTE)
    - Checks if user has completed settings
    - Checks if user has completed news preferences
    - Returns appropriate redirect URL
    """
    try:
        user_settings = db.query(UserSetting).filter(
            UserSetting.user_id==current_user.id
        ).first()

        news_preferences = db.query(NewsTopicAndScheduleTime).filter(
            NewsTopicAndScheduleTime.user_id==current_user.id
        ).first()

        if not user_settings:
            redirect_url = 'user-settings.html'
        elif not news_preferences:
            redirect_url = 'topic-and-schedule.html'
        else:
            redirect_url = 'news-summary.html'

        return {
            'redirect_url': redirect_url
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f'Error fetching redirect url: {exc}'
        )

# ============================================
# USER SETTINGS ENDPOINTS (Page 2)
# ============================================

@app.post('/user/setting')
async def create_user_settings(
    settings_data: UserSettingRequest,
    current_user: UserDetail = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifies user based on token
    Create user settings (country, city, API keys).
    Called when user completes the settings page.
    """
    try:
        #Step1: Verify user exists
        if not current_user:
            raise HTTPException(status_code=404, detail='User not found')

        #Step2: Create new user setting record
        new_settings_data = UserSetting(
            user_id=current_user.id,
            country=settings_data.country,
            city=settings_data.city,
            newsApi=settings_data.newsApi,
            weatherApi=settings_data.weatherApi
        )

        db.add(new_settings_data)
        db.commit()
        db.refresh(new_settings_data)
        
        return{
            'success_message': 'User Setting saved successfully'
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error creating settings: {str(exc)}'
        )

@app.put('/user/setting')
async def update_user_settings(
    settings_data: UserSettingRequest,
    current_user: UserDetail = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user
    Update user settings (partial update supported).
    Only updates fields that are provided in the request.
    """
    try:
        #Step1: Get current user
        settings = db.query(UserSetting).filter(
            UserSetting.user_id == current_user.id
        ).first()

        if not settings:
            raise HTTPException(
                status_code=404,
                detail='Settings not found. Use POST /settings/{user_id} to create.'
            )

        #Step2: Update only provided fields
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

@app.post('/news/preferences')
async def create_news_preferences(
    preference_data: NewsTopicScheduleRequest,
    current_user: UserDetail = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify existing user
    Create news preferences (topic and schedule).
    Called when user completes the news preferences page.
    """
    try:
        #Step1: Verify user exists
        if not current_user:
            raise HTTPException(status_code=404, detail='User not found')

        #Step2: Create new preferences
        new_preferences = NewsTopicAndScheduleTime(
            user_id=current_user.id,
            newsTopic=preference_data.newsTopic,
            isCustomTopic=preference_data.isCustomTopic,
            deliveryTime=preference_data.deliveryTime,
            isImmediate=preference_data.isImmediate,
            isScheduled=preference_data.isScheduled
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

@app.get('/news/preferences')
async def get_news_preferences(
    current_user: UserDetail = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all news preferences for a user.
    Returns a list since a user can have multiple preferences.
    """
    try:
        preferences = db.query(NewsTopicAndScheduleTime).filter(
            NewsTopicAndScheduleTime.user_id == current_user.id
        ).all()

        if not preferences:
            return {
                "message": "No preferences found for this user",
                "preferences": []
            }

        return {
            "user_id": current_user.id,
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

@app.put('/news/preferences/{preference_id}')
async def update_news_preferences(
    preference_id: int,
    preference_data: NewsTopicScheduleRequest,
    current_user: UserDetail = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update specific news preference by its ID.
    Supports partial updates.
    **Requires JWT authentication**
    """
    try:
        preference = db.query(NewsTopicAndScheduleTime).filter(
            NewsTopicAndScheduleTime.news_id == preference_id  
        ).first()

        if not preference:
            raise HTTPException(
                status_code=404,
                detail='Preference not found'
            )
        
        if preference.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail='You do not have permission to update this preference'
            )

        # Update only provided fields
        update_data = preference_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(preference, field, value)

        db.commit()
        db.refresh(preference)

    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f'Error updating preference: {str(exc)}'
        )

@app.delete('/news/preferences/{preference_id}')
async def delete_news_preference(
    preference_id: int,
    current_user: UserDetail = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific news preference"""
    try:
        preference = db.query(NewsTopicAndScheduleTime).filter(
            NewsTopicAndScheduleTime.news_id == preference_id
        ).first()

        if not preference:
            raise HTTPException(status_code=404, detail='Preference not found')

        if preference.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail='You do not have permission to delete this preference'
            )

        deleted_info = {
            "id": preference.news_id,
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