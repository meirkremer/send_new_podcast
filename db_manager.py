from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_schema import Base, Subscribers, RssPodcast, PodcastFiles
from typing import List, Tuple, Type
import os
import feedparser
import hashlib
import requests


class DatabaseManager:
    """
    A class for managing interactions with the podcast database.
    """

    def __init__(self) -> None:
        """
        Initialize the DatabaseManager.

        - Establishes a connection to the SQLite database.
        - Creates tables if they do not exist.
        - Initializes subscribers and RSS links.
        """

        # Init the SQLite database
        data_base_uri = 'sqlite:///database/podcast.db'
        engine = create_engine(data_base_uri)
        Base.metadata.create_all(engine)

        # Establishes connection to the database
        self._Session = sessionmaker(bind=engine)

        # Update subscribers
        self._init_subscribers()

        # Update RSS links
        self._init_rss()

    @staticmethod
    def _get_rss_feed_data(url: str) -> Tuple[str, str, bytes, str]:
        """
        Retrieve podcast headers data from an RSS feed

        Parameters:
            url (str): The URL of the RSS feed.

        Returns:
            tuple: A tuple containing: podcast title, description, podcast image, and image ID.
        """

        # Get the RSS-parsed data with feedparser
        rss = feedparser.parse(url)

        # Extract the necessary data about the podcast
        title = rss.feed.get('title')
        subtitle = rss.feed.get('subtitle')

        # The podcast image is obtained by extracting the image link and downloading the image
        image_href = rss.feed.get('image').get('href')
        response = requests.get(image_href)
        image = response.content if response.status_code == 200 else b''

        # Generate an image ID using a hash to prevent duplicates
        image_id = hashlib.md5()
        image_id.update(image)
        image_id = image_id.hexdigest()
        return title, subtitle, image, image_id

    def _init_subscribers(self) -> None:
        """
        Update subscribers based on a temporary file named subscribers.txt in temporary dir.
        The file template should be:
        email_address -- subscriber_name
        """

        # Extract the subscriber's data from the temporary file if its exist
        new_subscribers_file = 'temporary/subscribers.txt'
        if not os.path.exists(new_subscribers_file):
            return None
        with open(new_subscribers_file, 'r', encoding='utf-8') as f:
            new_subscribers = [subscriber.replace('\n', '') for subscriber in f.readlines() if len(subscriber) > 3]

        # Update the Subscribers table in the database
        session = self._Session()
        for subscriber in new_subscribers:
            email, name = subscriber.split(' -- ')

            subscriber_exist = session.query(Subscribers).filter_by(email=email).first()
            if subscriber_exist:
                continue

            new_subscriber = Subscribers(name=name, email=email)
            session.add(new_subscriber)

        # Commit the changes and delete the file
        session.commit()
        session.close()
        os.remove(new_subscribers_file)

    def _init_rss(self) -> None:
        """
        Update the RSS links based on a temporary file named rss.txt in temporary dir.
        The file template should be each rss link in one row
        """

        # Extract the RSS links from the temporary file if its exist
        rss_file = 'temporary/rss.txt'
        if not os.path.exists(rss_file):
            return None
        with open(rss_file, 'r', encoding='utf-8') as f:
            new_rss_links = [rss.replace('\n', '') for rss in f.readlines() if len(rss) > 3]

        # Update the rss table in the database
        session = self._Session()
        for rss_link in new_rss_links:
            rss_exist = session.query(RssPodcast).filter_by(rss_link=rss_link).first()
            if rss_exist:
                continue
            title, subtitle, image, image_id = self._get_rss_feed_data(rss_link)
            new_rss = RssPodcast(rss_link=rss_link,
                                 title=title,
                                 description=subtitle,
                                 image=image,
                                 image_id=image_id)
            session.add(new_rss)

        # Commit the changes and delete the temporary file
        session.commit()
        session.close()
        os.remove(rss_file)

    def fetch_all_rss(self) -> List[Type[RssPodcast]]:
        """
        Fetch all podcasts data include the RSS link from the database.

        Returns:
            List[Type[RssPodcast]]: A list of all RssPodcast objects.
        """

        session = self._Session()
        all_rss = session.query(RssPodcast).all()
        session.close()
        return all_rss

    def insert_podcast_file(self, podcast_id: int, drive_link: str, source_link: str, name: str,
                            description: str, size: int, duration: int, published_date: datetime) -> None:
        """
         Insert a new podcast file record into the database.

         Parameters:
             podcast_id (int): The ID of the associated podcast.
             drive_link (str): The Google Drive link for the podcast file.
             source_link (str): The source link of the podcast file.
             name (str): The name of the podcast file.
             description (str): The description of the podcast file.
             size (int): The size of the podcast file in bytes.
             duration (int): The duration of the podcast file in seconds.
             published_date (datetime): The published date of the podcast file.

         Returns:
             None
         """

        session = self._Session()
        new_podcast_file = PodcastFiles(
            podcast_id=podcast_id,
            drive_link=drive_link,
            source_link=source_link,
            name=name,
            description=description,
            size=size,
            duration=duration,
            published_date=published_date
        )
        session.add(new_podcast_file)
        session.commit()
        session.close()

    def fetch_unsent_podcast_files(self) -> List[Type[PodcastFiles]]:
        """
        Fetch all unsent podcast files from the database.

        Returns:
            List[PodcastFiles]: A list of unsent podcast file instances.
        """
        session = self._Session()
        all_unsent_podcast = session.query(PodcastFiles).filter_by(is_sent=0).all()
        session.close()
        return all_unsent_podcast

    def update_rss(self, rss_id: int, etag: str, last_newz_id: str = None, new_date: datetime = None) -> None:
        """
        Update the ETag, last newz date, and last newz ID in the database for an RSS podcast.

        Parameters:
            rss_id (int): The ID of the RSS podcast.
            etag (str): The new ETag value.
            last_newz_id (int, optional): The new last newz ID. Defaults to None.
            new_date (datetime, optional): The new last newz date. Defaults to None.

        Returns:
            None
        """

        session = self._Session()
        old_rss = session.query(RssPodcast).filter_by(id=rss_id).one()
        old_rss.e_tag = etag
        old_rss.last_newz = new_date if new_date else old_rss.last_newz
        old_rss.last_newz_id = last_newz_id if last_newz_id else old_rss.last_newz_id
        session.commit()
        session.close()

    def update_sent(self, file_id: int) -> None:
        """
        Update the is_sent field for PodcastFile record to 1 (True)

        Parameters:
            file_id (int): id of sent file

        Returns:
            None
        """
        session = self._Session()
        old_file = session.query(PodcastFiles).filter_by(id=file_id).one()
        old_file.is_sent = 1
        session.commit()
        session.close()

    def fetch_subscribers(self) -> List[Type[Subscribers]]:
        """
        Fetch all subscriber's data
        :return: list of subscriber's objects with subscriber's data
        """
        session = self._Session()
        all_subscribers = session.query(Subscribers).all()
        session.close()
        return all_subscribers
