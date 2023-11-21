import os.path
import re
import eyed3
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
    def __init__(self, podcast_list: list[Podcast], db: DatabaseManager):
        self._podcast_list = podcast_list
        self._db = db

    @staticmethod
    def _make_valid_file_name(file_name, ext):
        input_string = file_name.replace('_', ' ')
        pattern = r'[^a-zA-Z\dא-ת\s]'
        clean_string = re.sub(pattern, '', input_string)
        if len(clean_string) < 1:
            clean_string = 'untitled'
        return clean_string + ext

    @staticmethod
    def _get_drive_free_space(cred_path):
        drive_service = build('drive', 'v3', credentials=Credentials.from_service_account_file(cred_path))
        about = drive_service.about().get(fields='storageQuota').execute()
        free_space = int(about['storageQuota']['limit']) - int(about['storageQuota']['usage'])
        return free_space

    def _get_credential(self, file_size):
        cred_paths = [os.path.join('credentials', cred_name) for cred_name in os.listdir('credentials')
                      if cred_name.endswith('json')]
        for cred in cred_paths:
            if self._get_drive_free_space(cred) > file_size:
                return cred
        return None

    def _download_podcast(self, file_url, file_name):
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
        if response.status_code != 200:
            return None
        chunk_size = 1024 * 1024
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                f.write(chunk)
        return file_path

    @staticmethod
    def _upload_podcast(file_path, mime_type, description, credential_json):
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

    def _store_podcast_date(self, podcast_id, drive_link, source_link,
                            name, description, size, duration, published_date):
        self._db.insert_podcast_file(podcast_id, drive_link, source_link, name,
                                     description, size, duration, published_date)

    @staticmethod
    def _get_duration(file_path):
        audio_file = eyed3.load(file_path)
        if audio_file:
            return audio_file.info.time_secs
        else:
            return 0

    def get_all_podcast(self):
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
