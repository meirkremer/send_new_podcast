from time import time
from get_new_podcast import get_all_new_podcast
from datetime import datetime, timedelta
from db_manager import DatabaseManager
from files_manager import FilesManager
from logging_manager import loger
from create_email_message import create_mail_message
from send_email import send_email
import traceback


def main():
    """
    The main function that orchestrates the new podcast processing workflow.
    """

    loger.info('start running!')

    # Create db manager instance
    start_db_time = time()
    db = DatabaseManager()
    loger.debug(f'init db in: {(time() - start_db_time):.1f} seconds')

    # Get the new podcast from RSS
    yesterday = (datetime.now() - timedelta(days=1)).date()
    start_check_time = time()
    new_podcast = get_all_new_podcast(db, yesterday)
    loger.info(f'got {len(new_podcast)} new podcast, in {(time() - start_check_time):.1f} seconds')

    # If no new podcast receives exit without sending email
    if len(new_podcast) == 0:
        loger.info('no newz found! exit with out sending email')
        exit()

    # Download the podcast and then upload to googlDrive
    downloader = FilesManager(new_podcast, db)
    downloader.get_all_podcast()

    # Create the email message and send it to all members
    podcast_to_send = db.fetch_unsent_podcast_files()
    email_message = create_mail_message(podcast_to_send)

    send_email(db, email_message, podcast_to_send)


if __name__ == '__main__':
    start_run_time = time()
    try:
        # Execute all workflows for new podcasts
        main()
    except Exception as e:
        # Write general exception to log file
        tb = traceback.extract_tb(e.__traceback__)
        all_errors_message = f'\nerror details:\nall frames: {len(tb)}\n'
        for i, tb_f in enumerate(reversed(tb)):
            all_errors_message += f'frame number: {i + 1}\nfilename: {tb_f.filename}\nlineno: {tb_f.lineno}\n' \
                                  f'name: {tb_f.name}\ncode: {tb_f.line}\n\n'
        loger.error(all_errors_message)
    except SystemExit:
        # Write the run-time into the log file in case the exit() function is used during runtime
        loger.info(f'run time: {timedelta(seconds=(time() - start_run_time))}')
        exit()
    # Write the run-time into the log file
    loger.info(f'run time: {timedelta(seconds=(time()-start_run_time))}')
