# def send_auth_email(email: str, token: str):
#     # TEMP: replace with Mailtrap / Gmail later
#     print(f"[AUTH EMAIL] To: {email}")
#     print(f"Your login code: {token}")

from fastapi_mail import FastMail, MessageSchema
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from app.core.email import conf

env = Environment(loader=FileSystemLoader("app/templates/emails"))

fm = FastMail(conf)


async def send_auth_email(email: str, token: str):
    template = env.get_template("auth_code.html")
    html_content = template.render(token=token, year=datetime.utcnow().year)

    message = MessageSchema(
        subject="Your login code",
        recipients=[email],
        body=html_content,
        subtype="html",
    )

    await fm.send_message(message)
