
from services.api.app.agent.state import EmailInfo
from config import Settings
import smtplib
from email.message import EmailMessage


email_info = EmailInfo(
    from_="mariogj1987@gmail.com",
    to="mariogj1987@gmail.com",
    subject="Test Email from Monark Budget App",
    body="This is a test email sent from the Monark Budget application to verify email functionality.",
)


class SendEmail:

    def __init__(self,EmailInfo):
        self.from_ = EmailInfo.from_
        self.to = EmailInfo.to
        self.subject = EmailInfo.subject
        self.body = EmailInfo.body
        self.ADDRESS = Settings.SMTP_USER
        self.PASSWORD = Settings.SMTP_PASSWORD.get_secret_value()
    
    async def send_email_async(self):

        msg = EmailMessage()
        msg['Subject'] = self.subject
        msg['From'] = self.from_ 
        msg['To'] = self.to
        msg.set_content(self.body)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()  # upgrade the connection to TLS
            server.ehlo()
            server.login(self.ADDRESS, self.PASSWORD)
            server.send_message(msg)


if __name__ == "__main__":
    import asyncio

    email_sender = SendEmail(email_info)
    asyncio.run(email_sender.send_email_async())
    print("Test email sent successfully.")