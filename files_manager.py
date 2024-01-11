import os.path
import re
import eyed3
from typing import Union
from logging_manager import loger
from time import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaFileUpload
from db_manager import DatabaseManager
from get_new_podcast import Podcast
import requests


class FilesManager:
    """
    Manages the download and upload of podcast files to Google Drive.

    Attributes:
    - _podcast_list (list[Podcast]): List of Podcast objects to download and upload.
    - _db (DatabaseManager): Database manager to interact with the database.
    """
    def __init__(self, podcast_list: list[Podcast], db: DatabaseManager):
        """
        Initializes the FilesManager with the provided list of podcasts and a database manager.

        Parameters:
        - podcast_list (list[Podcast]): List of Podcast objects.
        - db (DatabaseManager): Instance of database manager.
        """
        self._podcast_list = podcast_list
        self._db = db

    @staticmethod
    def _make_valid_file_name(file_name: str, ext: str) -> str:
        """
        Generates a valid file name by removing invalid characters and adding the specified extension.

        Parameters:
        - file_name (str): Original file name.
        - ext (str): File extension.

        Returns:
        str: Valid file name with the specified extension.
        """
        max_words = 8
        input_string = file_name.replace('_', ' ')
        pattern = r'[^a-zA-Z\dא-ת\s]'
        clean_string = ' '.join(re.sub(pattern, '', input_string).split()[:max_words])
        if len(clean_string) < 1:
            clean_string = 'untitled'
        return clean_string + ext

    @staticmethod
    def _get_drive_free_space(cred_path: str) -> int:
        """
        Retrieves the free space available in Google Drive associated with the provided credentials.

        Parameters:
        - cred_path (str): Path to the JSON file containing Google Drive credentials.

        Returns:
        int: Free space available in Google Drive (in bytes).
        """
        drive_service = build('drive', 'v3', credentials=Credentials.from_service_account_file(cred_path))
        about = drive_service.about().get(fields='storageQuota').execute()
        free_space = int(about['storageQuota']['limit']) - int(about['storageQuota']['usage'])
        return free_space

    def _get_credential(self, file_size: int) -> Union[str, None]:
        """
        Selects a valid Google Drive credential file based on available free space.

        Parameters:
        - file_size (int): Size of the file to be uploaded.

        Returns:
        str | None: The path to the selected credential file is provided if it exists. If no credential file is found
         or there isn't enough storage space for the given size, 'None' is returned
        """
        cred_paths = [os.path.join('credentials', cred_name) for cred_name in os.listdir('credentials')
                      if cred_name.endswith('json')]
        for cred in cred_paths:
            if self._get_drive_free_space(cred) > file_size:
                return cred
        return None

    def _download_podcast(self, file_url: str, file_name: str) -> Union[str, None]:
        """
        Downloads a podcast file from the provided URL.

        Parameters:
        - file_url (str): URL of the podcast file.
        - file_name (str): Name of the podcast file.

        Returns:
        str or None: Path to the downloaded file or None if unsuccessful.
        """
        valid_file_name = self._make_valid_file_name(file_name, '.mp3')
        file_path = f'files/{valid_file_name}'
        try:
            response = requests.get(file_url, stream=True)
            content_type = response.headers.get('Content-Type', '')
            if 'audio/mpeg' not in content_type.lower():
                loger.warning(f'link: {file_url} not contain audio podcast. the content is: {content_type}')
                return None
        except requests.exceptions.ConnectionError as e:
            loger.error(e)
            return None
        except requests.exceptions.MissingSchema as e:
            loger.error(e)
            return None
        if response.status_code != 200:
            return None
        chunk_size = 1024 * 1024  # TODO: Check the optimal chunk size for download
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                f.write(chunk)
        return file_path

    @staticmethod
    def _upload_podcast(file_path: str, mime_type: str, description: str, credential_json: str) -> str:
        """
        Uploads a podcast file to Google Drive.

        Parameters:
        - file_path (str): Path to the local podcast file.
        - mime_type (str): MIME type of the file.
        - description (str): Description of the podcast episode.
        - credential_json (str): Path to the JSON file containing Google Drive credentials.

        Returns:
        str: Google Drive link to the uploaded file.
        """
        credentials = service_account.Credentials.from_service_account_file(
            credential_json,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        drive_service = build('drive', 'v3', credentials=credentials)
        file_metadata = {
            'name': os.path.basename(file_path),
            'description': description
        }
        media = MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        request = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        )
        response = None
        while response is None:
            status, response = request.next_chunk()
        permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        media.stream().close()
        drive_service.permissions().create(
            fileId=response['id'],
            body=permission
        ).execute()
        os.remove(file_path)
        return f"https://drive.google.com/file/d/{response['id']}/view"

    # TODO: it seams that this method not necessary and could be replace by insert_podcast_file
    def _store_podcast_date(self, podcast_id, drive_link, source_link,
                            name, description, size, duration, published_date):
        self._db.insert_podcast_file(podcast_id, drive_link, source_link, name,
                                     description, size, duration, published_date)

    @staticmethod
    def _get_duration(file_path: str) -> int:
        """
        Retrieves the duration of a given audio file path by eyed3

        :param file_path: Path to audio file
        :return: (int) file duration in seconds. Zero if unsuccessful get the duration
        """
        audio_file = eyed3.load(file_path)
        if audio_file:
            return int(audio_file.info.time_secs)
        else:
            return 0

    def get_all_podcast(self):
        """
        Download, upload, and store the data into the database for all podcast episodes in podcast_list
        :return: None
        """
        start_all_time = time()
        for podcast in self._podcast_list:
            start_podcast_time = time()
            file_url = podcast.source_link
            file_name = podcast.name
            file_path = self._download_podcast(file_url, file_name)
            if not file_path:
                loger.error(f'got None for podcast: {file_name}')
                continue
            duration = self._get_duration(file_path)
            description = podcast.description
            file_size = os.path.getsize(file_path)
            cred_path = self._get_credential(file_size)
            drive_link = self._upload_podcast(file_path, 'audio/mpeg', description, cred_path)
            self._db.insert_podcast_file(podcast.podcast_id, drive_link, file_url, file_name, description,
                                         file_size, duration, podcast.published_date)
            loger.info(f'download and upload file: {file_name} size: {(file_size / 1024 ** 2):.1f} MB '
                       f'in: {(time() - start_podcast_time):.1f} seconds')

        loger.info(f'download and upload {len(self._podcast_list)} podcast in {(time() - start_all_time):.1f} seconds')
