# get the new podcast until given date
import feedparser
import dicttoxml
from db_manager import DatabaseManager
from bs4 import BeautifulSoup
import time
from datetime import datetime
from logging_manager import loger


class Podcast:
    def __init__(self, podcast_id, name, source_link, description, published_date):
        self.podcast_id = podcast_id
        self.name = name
        self.source_link = source_link
        self.description = description
        self.published_date = published_date


def get_mp3_link(entry):
    xml_entry = dicttoxml.dicttoxml(dict(entry))
    soup = BeautifulSoup(xml_entry, 'xml')
    return next(iter([link.text for link in soup.find_all('href') if '.mp3' in link.text]), None)


def _get_new_podcast(db: DatabaseManager, podcast_id, rss_url, etag, old_newz_id, date):
    new_podcast = []

    start_check_time = time.time()
    feed = feedparser.parse(rss_url, etag=etag)
    loger.info(f'time to fetch rss {podcast_id}: {(time.time()-start_check_time):.1f} seconds')

    entries = feed.entries
    if not entries:
        loger.info('no newz receive. exit...')
        return new_podcast
    last_newz_id = ''
    last_newz_date = ''
    new_etag = feed.get('etag') if feed.get('etag') else ''
    start_check_time = time.time()
    for entry in entries:
        published = datetime.fromtimestamp(time.mktime(entry.get('published_parsed')))
        entry_id = entry.get('id')
        last_newz_id = entry_id if not last_newz_id else last_newz_id
        last_newz_date = published if not last_newz_date else last_newz_date

        if published.date() < date or entry_id == old_newz_id:
            break

        name = entry.get('title')
        source_link = get_mp3_link(entry)
        description = entry.get('summary')
        new_entry = Podcast(podcast_id, name, source_link, description, published)
        new_podcast.append(new_entry)

    db.update_rss(podcast_id, new_etag, last_newz_id, last_newz_date)
    loger.info(f'got {len(new_podcast)} new podcast. time to analyze: {(time.time() - start_check_time):.3f} seconds')

    return new_podcast


def get_all_new_podcast(db: DatabaseManager, date):
    all_new_podcast = []
    all_rss_url = [(rss.rss_link, rss.id, rss.e_tag, rss.last_newz_id) for rss in db.fetch_all_rss()]
    for rss_url, rss_id, etag, last_newz_id in all_rss_url:
        all_new_podcast += _get_new_podcast(db, rss_id, rss_url, etag, last_newz_id, date)
    return all_new_podcast
