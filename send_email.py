# TODO: all email sending manage will be move to difference server that will take care about subscribers
#  and send / receive emails
import smtplib
from logging_manager import loger
from db_manager import DatabaseManager
from db_schema import PodcastFiles
from private_conf import private_conf


def get_all_subscribers(db: DatabaseManager):
    all_subscribers = [subscriber.email for subscriber in db.fetch_subscribers()]
    return all_subscribers


def update_sent_podcast(sent_podcast: list[PodcastFiles], db: DatabaseManager):
    sent_podcast_id = [podcast.id for podcast in sent_podcast]
    for podcast_id in sent_podcast_id:
        db.update_sent(podcast_id)


def send_email(db, message, new_podcast: list[PodcastFiles]):
    sender_email = private_conf['sender_email_address']
    sender_password = private_conf['sender_email_password']
    subject = 'פודקאסטים חדשים'

    smtp_server = 'smtp.gmail.com'
    smtp_port = 587

    message['From'] = sender_email
    message['Subject'] = subject
    subscribers = get_all_subscribers(db)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, subscribers, message.as_string())
        print("Email sent successfully.")
        update_sent_podcast(new_podcast, db)
        return True
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        loger.error(e)
        return False
