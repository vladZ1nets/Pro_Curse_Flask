from celery import Celery
import os

from sqlalchemy import select

from database import init_db, db_session
from models import Item, Contract

app = Celery('tasks', broker=f'pyamqp://guest@{os.environ.get("RABBITMQ_HOST", "localhost")}//')

@app.task
def add(x, y):
    print(x + y)


@app.task
def send_email(contract_id):
    # Import smtplib for the actual sending function
    import smtplib

    # Import the email modules we'll need
    from email.message import EmailMessage

    init_db()
    contract = db_session.execute(select(Contract).filter_by(id=contract_id)).scalar()
    item = db_session.execute(select(Item).filter_by(id=contract.item)).scalar()

    import smtplib
    # creates SMTP session
    s = smtplib.SMTP('smtp.gmail.com', 587)
    # start TLS for security
    s.starttls()
    # Authentication
    s.login("sender_email_id", "sender_email_id_password")
    # message to be sent
    message = "Message_you_need_to_send"
    # sending the mail
    s.sendmail("appemail@example.com", "user1@gmail.com", message)
    s.sendmail("appemail@example.com", "user2@gmail.com", message)
    # terminating the session
    s.quit()