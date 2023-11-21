# create database class for manage the database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_schema import Base, Subscribers, RssPodcast, PodcastFiles
import os
import feedparser
import hashlib
import requests


class DatabaseManager:
    def __init__(self):
        data_base_uri = 'sqlite:///database/podcast.db'
        engine = create_engine(data_base_uri)
        Base.metadata.create_all(engine)
        self._Session = sessionmaker(bind=engine)

        # update subscribers
        self._init_subscribers()

        # update rss links
        self._init_rss()

    @staticmethod
    def get_rss_feed_data(url):
        rss = feedparser.parse(url)
        title = rss.feed.get('title')
        subtitle = rss.feed.get('subtitle')
        image_href = rss.feed.get('image').get('href')
        response = requests.get(image_href)
        image = response.content if response.status_code == 200 else b''
        image_id = hashlib.md5()
        image_id.update(image)
        image_id = image_id.hexdigest()
        return title, subtitle, image, image_id

    def _init_subscribers(self):
        new_subscribers_file = 'temporary/subscribers.txt'
        if not os.path.exists(new_subscribers_file):
            return None
        with open(new_subscribers_file, 'r', encoding='utf-8') as f:
            new_subscribers = [subscriber.replace('\n', '') for subscriber in f.readlines() if len(subscriber) > 3]

        session = self._Session()
        for subscriber in new_subscribers:
            email, name = subscriber.split(' -- ')

            subscriber_exist = session.query(Subscribers).filter_by(email=email).first()
            if subscriber_exist:
                continue

            new_subscriber = Subscribers(name=name, email=email)
            session.add(new_subscriber)

        session.commit()

        os.remove(new_subscribers_file)

    def _init_rss(self):
        rss_file = 'temporary/rss.txt'
        if not os.path.exists(rss_file):
            return None
        with open(rss_file, 'r', encoding='utf-8') as f:
            new_rss_links = [rss.replace('\n', '') for rss in f.readlines() if len(rss) > 3]

        session = self._Session()
        for rss_link in new_rss_links:
            rss_exist = session.query(RssPodcast).filter_by(rss_link=rss_link).first()
            if rss_exist:
                continue
            title, subtitle, image, image_id = self.get_rss_feed_data(rss_link)
            new_rss = RssPodcast(rss_link=rss_link,
                                 title=title,
                                 description=subtitle,
                                 image=image,
                                 image_id=image_id)
            session.add(new_rss)

        session.commit()

        os.remove(rss_file)

    def fetch_all_rss(self):
        session = self._Session()
        all_rss = session.query(RssPodcast).all()
        return all_rss

    def insert_podcast_file(self, podcast_id, drive_link, source_link, name,
                            description, size, duration, published_date):
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

    def fetch_unsent_podcast_files(self):
        session = self._Session()
        all_unsent_podcast = session.query(PodcastFiles).filter_by(is_sent=0).all()
        return all_unsent_podcast

    def update_rss(self, rss_id, etag, last_newz_id=None, new_date=None):
        # update etag and last newz date
        session = self._Session()
        old_rss = session.query(RssPodcast).filter_by(id=rss_id).one()
        old_rss.e_tag = etag
        old_rss.last_newz = new_date if new_date else old_rss.last_newz
        old_rss.last_newz_id = last_newz_id if last_newz_id else old_rss.last_newz_id
        session.commit()
        session.close()

    def update_sent(self, file_id):
        session = self._Session()
        old_file = session.query(PodcastFiles).filter_by(id=file_id).one()
        old_file.is_sent = 1
        session.commit()
        session.close()

    def fetch_subscribers(self):
        session = self._Session()
        all_subscribers = session.query(Subscribers).all()
        return all_subscribers


def test():
    db = DatabaseManager()
    all_rss = [rss.title + '\n' + rss.rss_link + '\n' for rss in db.fetch_all_rss()]
    print('\n'.join(all_rss))
    all_subscribers = [subscriber.name + subscriber.email + '\n' for subscriber in db.fetch_subscribers()]
    print('\n'.join(all_subscribers))


if __name__ == '__main__':
    test()
