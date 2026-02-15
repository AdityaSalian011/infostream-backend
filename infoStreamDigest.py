import logging
from typing import List, Dict, Optional, Tuple
from models import UserDetail, UserSetting, NewsTopicAndScheduleTime
from database import get_db
from sqlalchemy.orm import Session
from fastapi import Depends
from jinja2 import Environment, FileSystemLoader
from config import TEMPLATE_FOLDER, HTML_TEMPLATE

# Import APIs
from news.news import NewsAPI
from weather.weather import WeatherAPI
from stock.stock import StockAPI
from html_email.html_email import HTMLEmail

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('infostream.log'),  # Log to file
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)


class InfoStreamDigest:
    def __init__(self):
        self.news_api = NewsAPI()
        self.weather_api = WeatherAPI()
        self.stock_api = StockAPI()
        self.html_email = HTMLEmail()

    def get_users_to_notify(
        self, 
        db: Session, 
        target_time: Optional[str] = None
    ):
        """
        Fetch users who should receive news digest.
        
        Args:
            db: Database session
            target_time: Optional time filter (e.g., "09:00" for scheduled delivery)
            
        Returns:
            Tuple of (user_data_list, error_message)
        """
        try:
            query = db.query(
                UserDetail.id,
                UserDetail.email,
                UserSetting.city,
                UserSetting.newsApi,
                UserSetting.weatherApi,
                NewsTopicAndScheduleTime.newsTopic,
                NewsTopicAndScheduleTime.deliveryTime,
            ).join(
                UserSetting,
                UserDetail.id == UserSetting.user_id
            ).join(
                NewsTopicAndScheduleTime,
                UserDetail.id == NewsTopicAndScheduleTime.user_id
            )
            
            # Filter by delivery time if provided
            if target_time:
                query = query.filter(
                    NewsTopicAndScheduleTime.deliveryTime == target_time
                )
            
            results = query.all()
            
            if not results:
                logger.info(f"No users found for target_time: {target_time}")
                return [], None

            # Group data by user
            user_data_map = {}
            
            for row in results:
                user_id = row[0]

                # Initialize user if not seen before
                if user_id not in user_data_map:
                    user_data_map[user_id] = {
                        'id': row[0],
                        'email': row[1],
                        'city': row[2],
                        'news_api_key': row[3],
                        'weather_api_key': row[4],
                        'news_preferences': []  # FIX: Initialize the list!
                    }

                # Add news preference to user's list
                user_data_map[user_id]['news_preferences'].append({
                    'news_topic': row[5],
                    'delivery_time': row[6],
                })

            user_data = list(user_data_map.values())
            logger.info(f"Found {len(user_data)} users to notify")
            
            return user_data, None

        except Exception as exc:
            error_msg = f'Database error while fetching users: {str(exc)}'
            logger.error(error_msg, exc_info=True)
            return [], error_msg

    def _generate_html(
        self, 
        news_topic: str, 
        city_name: str,
        news_api_key: str,
        weather_api_key: str
    ):
        """
        Generate HTML content from current data.
        
        Args:
            news_topic: Topic for news articles
            city_name: City for weather data
            
        Returns:
            Tuple of (rendered_html, error_message)
        """
        try:
            # Fetch news data
            logger.info(f"Fetching news for topic: {news_topic}")
            news_data = self.news_api.get_top_news(
                topic=news_topic,
                api_key=news_api_key
            )
            
            # Check if error was returned as string
            if isinstance(news_data, str):
                return None, f'News API error: {news_data}'
            
            if not news_data:
                logger.warning(f"No news articles found for topic: {news_topic}")
                return None, 'No news articles available'

            # Fetch weather data
            logger.info(f"Fetching weather for city: {city_name}")
            weather_data = self.weather_api.get_weather_info(
                city_name=city_name,
                api_key=weather_api_key
            )
            
            if isinstance(weather_data, str):
                return None, f'Weather API error: {weather_data}'

            # Fetch stock data
            logger.info("Fetching stock data")
            stock_data = self.stock_api.get_stock_data()
            
            if isinstance(stock_data, str):
                return None, f'Stock API error: {stock_data}'
            
            # Render HTML template
            env = Environment(loader=FileSystemLoader(TEMPLATE_FOLDER))
            template = env.get_template(HTML_TEMPLATE)

            rendered_html = template.render(
                data=news_data,
                weather_info=weather_data['weather_info'],
                weather_icon_url=weather_data['weather_icon_url'],
                stock_info=stock_data
            )
            
            logger.info("HTML generated successfully")
            return rendered_html, None
            
        except FileNotFoundError as exc:
            error_msg = f'Template file not found: {str(exc)}'
            logger.error(error_msg)
            return None, error_msg
            
        except KeyError as exc:
            error_msg = f'Missing required data field: {str(exc)}'
            logger.error(error_msg, exc_info=True)
            return None, error_msg
            
        except Exception as exc:
            error_msg = f'Error generating HTML: {str(exc)}'
            logger.error(error_msg, exc_info=True)
            return None, error_msg

    def send_email_to_user(
        self, 
        user_email: str, 
        news_topic: str, 
        city_name: str,
        news_api_key: str,
        weather_api_key: str
    ):
        """
        Send personalized news digest to a single user.
        
        Args:
            user_email: Recipient email address
            news_topic: News topic for this user
            city_name: User's city for weather
            
        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        try:
            # Generate HTML content
            rendered_html, html_error = self._generate_html(
                news_topic, 
                city_name,
                news_api_key,
                weather_api_key
            )
            
            if html_error:
                logger.error(
                    f"Failed to generate HTML for {user_email}: {html_error}"
                )
                return False, html_error

            # Send email
            logger.info(f"Sending email to {user_email}")
            email_sent, email_error = self.html_email.send_html_content(
                to_email=user_email,
                subject=f"Your {news_topic.title()} News Digest",
                html_content=rendered_html
            )
            
            if not email_sent:
                logger.error(
                    f"Failed to send email to {user_email}: {email_error}"
                )
                return False, email_error
            
            logger.info(f"Successfully sent email to {user_email}")
            return True, None
            
        except Exception as exc:
            error_msg = f'Unexpected error sending email to {user_email}: {str(exc)}'
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def send_emails_batch(
        self, 
        db: Session = Depends(get_db), 
        target_time: Optional[str] = None
    ):
        """
        Send news digests to all users scheduled for a specific time.
        THIS IS THE MAIN METHOD TO BE CALLED BY YOUR SCHEDULER.
        
        Args:
            db: Database session
            target_time: Time filter for scheduled emails (e.g., "09:00")
            
        Returns:
            Summary dictionary with success/failure counts
            
        Example:
            digest = InfoStreamDigest()
            result = digest.send_emails_batch(db, target_time="09:00")
            print(result)
            # {'status': 'success', 'total_users': 10, 'emails_sent': 10, ...}
        """
        logger.info(f"Starting batch email job for time: {target_time}")
        
        # Get users to notify
        users, db_error = self.get_users_to_notify(db, target_time)
        
        if db_error:
            return {
                'status': 'error',
                'message': db_error,
                'total_users': 0,
                'emails_sent': 0,
                'emails_failed': 0,
                'errors': []
            }
        
        if not users:
            return {
                'status': 'success',
                'message': 'No users to notify',
                'total_users': 0,
                'emails_sent': 0,
                'emails_failed': 0,
                'errors': []
            }
        
        # Send emails to each user
        emails_sent = 0
        emails_failed = 0
        errors = []
        
        for user in users:
            user_email = user['email']
            city = user['city']
            news_api_key = user['news_api_key']
            weather_api_key = user['weather_api_key']
            
            # Handle multiple news topics per user
            for preference in user['news_preferences']:
                news_topic = preference['news_topic']
                
                success, error = self.send_email_to_user(
                    user_email=user_email,
                    news_topic=news_topic,
                    city_name=city,
                    news_api_key=news_api_key,
                    weather_api_key=weather_api_key
                )
                
                if success:
                    emails_sent += 1
                else:
                    emails_failed += 1
                    errors.append({
                        'user_email': user_email,
                        'news_topic': news_topic,
                        'error': error
                    })
        
        # Return summary
        result = {
            'status': 'success' if emails_failed == 0 else 'partial_success',
            'total_users': len(users),
            'emails_sent': emails_sent,
            'emails_failed': emails_failed,
            'errors': errors
        }
        
        logger.info(
            f"Batch job complete. Sent: {emails_sent}, "
            f"Failed: {emails_failed}, Total users: {len(users)}"
        )
        
        return result

    def send_immediate_email(
        self,  
        db: Session
    ):
        """
        Send an immediate email to a specific user (for on-demand requests).
        Use this when a user clicks "Send Now" instead of waiting for scheduled time.
        
        Args:
            user_id: User ID to send email to
            db: Database session
            
        Returns:
            Result dictionary
            
        Example:
            digest = InfoStreamDigest()
            result = digest.send_immediate_email(user_id=123, db=db)
        """
        try:
            # Fetch user data
            user_data = db.query(
                UserDetail.id,
                UserDetail.email,
                UserSetting.city,
                UserSetting.newsApi,
                UserSetting.weatherApi,
                NewsTopicAndScheduleTime.news_id,
                NewsTopicAndScheduleTime.newsTopic
            ).join(
                UserSetting,
                UserDetail.id == UserSetting.user_id
            ).join(
                NewsTopicAndScheduleTime,
                UserDetail.id == NewsTopicAndScheduleTime.user_id
            ).filter(
                NewsTopicAndScheduleTime.isImmediate == True
            ).all()
            
            if not user_data:
                return {
                    'status': 'error',
                    'message': 'User not found or not configured for immediate emails',
                    'emails_sent': 0,
                    'emails_failed': 0
                }
            
            # Group data by user_id
            users_map = {}
            for row in user_data:
                user_id = row[0]

                if user_id not in users_map:
                    users_map[user_id] = {
                        'email': row[1],
                        'city': row[2],
                        'news_api_key': row[3],
                        'weather_api_key': row[4],
                        'news_preference': []
                    }

                users_map[user_id]['news_preference'].append({
                    'schedule_id': row[5],
                    'news_topic': row[6]
                })

            # Track results
            total_users = len(users_map)
            total_emails_sent = 0
            total_emails_failed = 0
            all_errors = []
            all_schedule_ids_to_reset = []

            # Process each user
            for user_id, user_info in users_map.items():
                email = user_info['email']
                city = user_info['city']
                news_api_key = user_info['news_api_key']
                weather_api_key = user_info['weather_api_key']

                logger.info(f"Processing immediate emails for user: {email}")

                ## Send email for each news topic this user requested
                for pref in user_info['news_preference']:
                    schedule_id = pref['schedule_id']
                    news_topic = pref['news_topic']

                    logger.info(f"Sending immediate email to {email} for topic: {news_topic}")

                    success, error = self.send_email_to_user(
                        user_email=email,
                        news_topic=news_topic,
                        city_name=city,
                        news_api_key=news_api_key,
                        weather_api_key=weather_api_key
                    )

                    if success:
                        total_emails_sent += 1
                        all_schedule_ids_to_reset.append(schedule_id)
                        logger.info(f'Successfully sent {news_topic} email to {email}')

                    else:
                        total_emails_failed += 1
                        all_errors.append({
                            'news_topic': news_topic,
                            'error': error
                        })
                        logger.error(f"Failed to send {news_topic} email to {email}: {error}")

            # Reset isImmediate flag for successfully sent emails
            if all_schedule_ids_to_reset:
                db.query(NewsTopicAndScheduleTime).filter(
                    NewsTopicAndScheduleTime.news_id.in_(all_schedule_ids_to_reset)
                ).update(
                    {'isImmediate': False}, synchronize_session=False
                )

                db.commit()
                logger.info(f"Reset isImmediate flag for {len(all_schedule_ids_to_reset)} schedules")

            # Determine overall status
            if total_emails_failed == 0:
                status = 'success'
            elif total_emails_sent > 0:
                status = 'partial_success'
            else:
                status = 'error'
            
            result = {
                'status': status,
                'message': f'Processed {total_users} user(s): sent {total_emails_sent} email(s), {total_emails_failed} failed',
                'total_users': total_users,
                'emails_sent': total_emails_sent,
                'emails_failed': total_emails_failed,
                'errors': all_errors
            }
            
            logger.info(f"Immediate email batch complete: {result}")
            return result
                    
        except Exception as exc:
            error_msg = f'Error sending immediate emails: {str(exc)}'
            logger.error(error_msg, exc_info=True)
            return {
                'status': 'error',
                'message': error_msg,
                'total_users': 0,
                'emails_sent': 0,
                'emails_failed': 0,
                'errors': [str(exc)]
            }

# ============================================
# EXAMPLE USAGE WITH SCHEDULER
# ============================================
"""
Example with APScheduler:

from apscheduler.schedulers.background import BackgroundScheduler
from database import SessionLocal

def scheduled_job():
    db = SessionLocal()
    try:
        digest = InfoStreamDigest()
        result = digest.send_emails_batch(db, target_time="09:00")
        logger.info(f"Job result: {result}")
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_job, 'cron', hour=9, minute=0)
scheduler.start()
"""

# ============================================
# EXAMPLE USAGE WITH FASTAPI
# ============================================
"""
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db

app = FastAPI()
digest = InfoStreamDigest()

@app.post("/send-immediate/{user_id}")
def send_immediate(user_id: int, db: Session = Depends(get_db)):
    result = digest.send_immediate_email(user_id, db)
    if result['status'] == 'error':
        raise HTTPException(status_code=400, detail=result['message'])
    return result

@app.post("/send-batch")
def send_batch(target_time: str, db: Session = Depends(get_db)):
    result = digest.send_emails_batch(db, target_time)
    return result
"""