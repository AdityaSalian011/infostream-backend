import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@yourdomain.com')

class HTMLEmail:
    def send_html_content(self, to_email, html_content, subject):
        """A method to send html email at the given address"""
        try:
            if not SENDGRID_API_KEY:
                return None, 'SENDGRID_API_KEY not configured'
            
            message = Mail(
                from_email=FROM_EMAIL,
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )

            sg = SendGridAPIClient(SENDGRID_API_KEY)
            response = sg.send(message)

            logger.info(f"✅ Email sent to {to_email} (Status: {response.status_code})")
            return 'Email sent successfully', None
        except Exception as exc:
            error = f'Failed to send email:\n{exc}'
            logger.error(error)
            return None, error
        
if __name__=='__main__':
    email = HTMLEmail()
    success, error = email.send_html_content('adityasalian06@gmail.com', 'TEST', 'test')
    print(success)
    print(error)