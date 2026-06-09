import asyncio
import resend
from jinja2 import Environment, FileSystemLoader
from datetime import datetime

from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY
env = Environment(loader=FileSystemLoader("app/templates/emails"))

async def send_auth_email(email: str, token: str):
    # so as to copy code from terminal
    if not resend.api_key:
        print(f"[AUTH EMAIL - FALLBACK] To: {email}")
        print(f"Your login code: {token}")
        print("Note: RESEND_API_KEY is not set.")
        return

    template = env.get_template("auth_code.html")
    html_content = template.render(token=token, year=datetime.utcnow().year)

    def _send():
        return resend.Emails.send({
            "from": "Maigidaje Hidaya Mannir<maigidaje@daneena-ea-tts.buzz/>",
            "to": email,
            "subject": "Your login code",
            "html": html_content
        })

    await asyncio.to_thread(_send)
