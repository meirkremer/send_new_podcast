import feedparser
from feedparser.util import FeedParserDict
import dicttoxml
from db_manager import DatabaseManager
from bs4 import BeautifulSoup
import time
from datetime import datetime
from logging_manager import loger
from typing import Union


class Podcast:
    """
    Represents a podcast entry with basic information.

    Attributes:
    - podcast_id (int): ID of the podcast class.
    - name (str): Name of the podcast episode.
    - source_link (str): Source link to the podcast.
    - description (str): Description of the podcast.
    - published_date (datetime): Date and time when the podcast was published.
    """
    def __init__(self, podcast_id: int, name: str, source_link: str, description: str, published_date: datetime):
        """
        Init the podcast instance with given details
        :param podcast_id: (int): ID of the podcast class.
        :param name: (str): Name of the podcast episode.
        :param source_link: (str): Source link to the podcast.
        :param description: (str): Description of the podcast.
        :param published_date: (datetime): Date and time when the podcast was published.
        """
        self.podcast_id = podcast_id
        self.name = name
        self.source_link = source_link
        self.description = description
        self.published_date = published_date


def _get_mp3_link(entry: FeedParserDict) -> Union[str, None]:
    """
    Extracts the MP3 link from a podcast entry using dictoxml and BeautifulSoup.

    Parameters:
    - entry (FeedParserDict): Podcast entry dictionary.

    Returns:
    str or None: MP3 link if found, otherwise None.
    """
    xml_entry = dicttoxml.dicttoxml(dict(entry))
    soup = BeautifulSoup(xml_entry, 'xml')
    return next(iter([link.text for link in soup.find_all('href') if '.mp3' in link.text]), None)


def _get_new_podcast(db: DatabaseManager, podcast_id: int, rss_url: str,
                     etag: str, old_newz_id: str, date: datetime) -> list[Podcast]:
    """
    Fetches details of new podcast episodes from the specified RSS feed until the given date.
    :param db: Database manager instance to update the RSS details with the new ETag, last entry ID, and date.
    :param podcast_id: The unique identifier of the podcast class.
    :param rss_url: The URL of the RSS feed to retrieve podcast episode details from.
    :param etag: The ETag string for quick checking of new episodes.
    :param old_newz_id: The ID string of the last known episode.
    :param date: The last date to consider for retrieving updates. Only the date part is considered, time is ignored.
    :return: A list of Podcast objects containing details of all new podcast episodes.
    """

    new_podcast = []

    # get the RSS feed data
    start_check_time = time.time()
    feed = feedparser.parse(rss_url, etag=etag)
    loger.debug(f'time to fetch rss {podcast_id}: {(time.time()-start_check_time):.1f} seconds')

    entries = feed.entries
    if not entries:
        loger.debug('no newz receive. exit...')
        return new_podcast
    last_newz_id = ''
    last_newz_date = ''
    new_etag = feed.get('etag') if feed.get('etag') else ''

    # analyze the new episodes
    start_check_time = time.time()
    for entry in entries:
        published = datetime.fromtimestamp(time.mktime(entry.get('published_parsed')))
        entry_id = entry.get('id')
        last_newz_id = entry_id if not last_newz_id else last_newz_id
        last_newz_date = published if not last_newz_date else last_newz_date

        if published.date() < date or entry_id == old_newz_id:
            break

        name = entry.get('title')
        source_link = _get_mp3_link(entry)
        description = entry.get('summary')
        new_entry = Podcast(podcast_id, name, source_link, description, published)
        new_podcast.append(new_entry)

    db.update_rss(podcast_id, new_etag, last_newz_id, last_newz_date)
    loger.info(f'got {len(new_podcast)} new podcast. time to analyze: {(time.time() - start_check_time):.3f} seconds')

    return new_podcast


def get_all_new_podcast(db: DatabaseManager, date: datetime) -> list[Podcast]:
    """
    Get the all new podcast episodes until the given date
    :param db: Database manager instance to fetch and update the RSS data
    :param date: datetime object with only a date
    :return: list with Podcast instance represent the all new podcast episodes
    """
    all_new_podcast = []
    all_rss_url = [(rss.rss_link, rss.id, rss.e_tag, rss.last_newz_id) for rss in db.fetch_all_rss()]
    for rss_url, rss_id, etag, last_newz_id in all_rss_url:
        all_new_podcast += _get_new_podcast(db, rss_id, rss_url, etag, last_newz_id, date)
    return all_new_podcast
