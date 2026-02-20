import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
logger = logging.getLogger(__name__)

class HTMLEmail:
    def send_html_content(self, to_email, html_content, subject):
        """A method to send html email at the given address"""
        try:
            from_email = os.getenv('FROM_EMAIL')
            gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')

            if not from_email or not gmail_app_password:
                return None, 'Gmail credentials not configured'
            
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = from_email
            message['To'] = to_email
            message.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(from_email, gmail_app_password)
                server.sendmail(from_email, to_email, message.as_string())

            logger.info(f"✅ Email sent to {to_email}")
            return 'Email sent successfully', None
        except Exception as exc:
            error = f'Failed to send email:\n{exc}'
            logger.error(error)
            return None, error
        
if __name__=='__main__':
    email = HTMLEmail()
    success, error = email.send_html_content('adityasalian011@gmail.com', 'TEST', 'test')
    print(success)
    print(error)