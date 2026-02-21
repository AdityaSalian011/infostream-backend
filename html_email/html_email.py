import os
import logging
import requests
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
logger = logging.getLogger(__name__)

class HTMLEmail:
    def send_html_content(self, to_email, html_content, subject):
        """A method to send html email at the given address"""
        try:
            from_email = os.getenv('FROM_EMAIL')
            smtp_key = os.getenv('SMTP_KEY')

            if not from_email or not smtp_key:
                return None, 'Gmail credentials not configured'
            
            response = requests.post(
                'https://api.brevo.com/v3/smtp/email',
                headers={
                    'api-key': smtp_key,
                    'Content-Type': 'application/json'
                },
                json={
                    'sender': {'email': from_email},
                    'to': [{'email': to_email}],
                    'subject': subject,
                    'htmlContent': html_content
                }
            )

            if response.status_code == 201:
                logger.info(f"✅ Email sent to {to_email}")
                return 'Email sent successfully', None
            else:
                error = f'Brevo error: {response.status_code} - {response.text}'
                logger.error(error)
                return None, error
            
        except Exception as exc:
            error = f'Failed to send email:\n{exc}'
            logger.error(error)
            return None, error
        
if __name__=='__main__':
    email = HTMLEmail()
    success, error = email.send_html_content('adityasalian011@gmail.com', 'TEST', 'test')
    print(success)
    print(error)