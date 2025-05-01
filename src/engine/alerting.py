import logging
import smtplib
from email.message import EmailMessage
from smtplib import SMTPResponseException

from engine.config import SECRETS

log = logging.getLogger(__name__)


def alert_via_email(alert: str, destination_email: str = SECRETS['GMAIL_ALERT_EMAIL']) -> None:
    msg = EmailMessage()
    msg['Subject'] = 'Edinburgh Crowds Alert'
    msg['From'] = 'info@edinburghcrowds.co.uk'
    msg['To'] = destination_email
    msg.set_content(alert)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(SECRETS['GMAIL_ALERT_EMAIL'], SECRETS['GMAIL_ALERT_APP_PASSWORD'])
            smtp.send_message(msg)
            log.info(f'Sent email alert to {msg["To"]}')
    except SMTPResponseException as e:
        log.error(f'Email was not delivered; SMTP error: {e.smtp_code} - {e.smtp_error.decode(errors="ignore")}')
