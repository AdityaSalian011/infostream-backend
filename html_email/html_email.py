import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

from config import (
    SMTP_SERVER,
    SMTP_PORT,
    FROM_EMAIL
)

load_dotenv()
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

class HTMLEmail:
    def send_html_content(self, to_email, html_content, subject):
        """A method to send html email at the given address"""
        try:
            from_email = FROM_EMAIL    ## my email address
            app_password = SMTP_PASSWORD           ## my password

            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(html_content, 'html'))  ## attaches html content

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()   
                server.login(from_email, app_password)
                server.send_message(msg)
            
            return 'Email sent successfully', None
        except Exception as exc:
            error = f'Failed to send email:\n{exc}'
            return None, error
        
if __name__=='__main__':
    email = HTMLEmail()
    success, error = email.send_html_content('adityasalian06@gmail.com', 'TEST', 'test')
    print(success)
    print(error)