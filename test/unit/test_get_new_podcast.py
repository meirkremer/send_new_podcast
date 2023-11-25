import os
import feedparser
import get_new_podcast
import pytest


@pytest.fixture
def get_feed_parser_entry():
    rss_url = 'https://www.omnycontent.com/d/playlist/2ee97a4e-8795-4260-9648-accf00a38c6a/a5d4b51f-5b9e-43db-' \
              '84da-ace100c04108/0ab18f83-1327-4f4e-9d7a-ace100c0411f/podcast.rss'
    test_entry_id = 'd079955c-6fc3-4ea4-ae0d-b0c1015e7da6'
    entries = feedparser.parse(rss_url).entries
    for entry in entries:
        if entry.get('id') == test_entry_id:
            return entry


def test_get_mp3_link(get_feed_parser_entry):
    print(f'\nwork dir: {os.getcwd()}\n')
    result = get_new_podcast._get_mp3_link(get_feed_parser_entry)
    mp3_link = 'https://traffic.omny.fm/d/clips/2ee97a4e-8795-4260-9648-accf00a38c6a/a5d4b51f-5b9e-43db-84da-ace100c' \
               '04108/d079955c-6fc3-4ea4-ae0d-b0c1015e7da6/audio.mp3?utm_source=Podcast&in_playlist=0ab18f' \
               '83-1327-4f4e-9d7a-ace100c0411f'
    assert result == mp3_link
