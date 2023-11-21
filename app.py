from time import time
from get_new_podcast import get_all_new_podcast
from datetime import datetime, timedelta
from db_manager import DatabaseManager
from files_manager import FilesManager
from logging_manager import loger
from create_email_message import create_mail_message
from send_email import send_email


def main():
    loger.info('start running!')

    # create db manager instance
    start_db_time = time()
    db = DatabaseManager()
    loger.debug(f'init db in: {(time() - start_db_time):.1f} seconds')

    # get the new podcast from rss
    yesterday = (datetime.now() - timedelta(days=1)).date()
    start_check_time = time()
    new_podcast = get_all_new_podcast(db, yesterday)
    loger.info(f'got {len(new_podcast)} new podcast, in {(time() - start_check_time):.1f} seconds')

    # if no new podcast receives exit without sending email
    if len(new_podcast) == 0:
        loger.info('no newz found! exit with out sending email')
        exit()

    # download the podcast and then upload to googlDrive
    downloader = FilesManager(new_podcast, db)
    downloader.get_all_podcast()

    # create the email message and send it to all members
    podcast_to_send = db.fetch_unsent_podcast_files()
    email_message = create_mail_message(podcast_to_send)

    send_email(db, email_message, podcast_to_send)


if __name__ == '__main__':
    start_run_time = time()
    try:
        main()
    except Exception as e:
        loger.error(e)
    except SystemExit:
        loger.info(f'run time: {timedelta(seconds=(time() - start_run_time))}')
        exit()
    loger.info(f'run time: {timedelta(seconds=(time()-start_run_time))}')
