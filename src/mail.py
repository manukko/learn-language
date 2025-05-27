from fastapi_mail import FastMail, ConnectionConfig, MessageSchema, MessageType
import os
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT"))  # default if missing
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent

mail_config = ConnectionConfig(
    MAIL_USERNAME= MAIL_USERNAME,
    MAIL_PASSWORD= MAIL_PASSWORD,
    MAIL_PORT= MAIL_PORT,
    MAIL_SERVER= MAIL_SERVER,
    MAIL_FROM= MAIL_FROM,
    MAIL_FROM_NAME= MAIL_FROM_NAME,
    MAIL_STARTTLS= True,
    MAIL_SSL_TLS= False,
    USE_CREDENTIALS= True,
    VALIDATE_CERTS= True,
    # TEMPLATE_FOLDER= Path(BASE_DIR, 'templates')
)

mail = FastMail(config=mail_config)

def create_message(subject: str, recipients: list[str], body: str):
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=MessageType.html
    )
    return message

