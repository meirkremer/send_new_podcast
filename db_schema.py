# defined the db schema for podcast and users
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, LargeBinary, DateTime, ForeignKey

Base = declarative_base()


# defined table for subscribers to send the podcast
class Subscribers(Base):
    __tablename__ = 'subscribers'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)


# defined table for rss links
class RssPodcast(Base):
    __tablename__ = 'rss_podcast'
    id = Column(Integer, primary_key=True)
    rss_link = Column(String, unique=True)
    e_tag = Column(String, default='')
    title = Column(String)
    description = Column(String)
    image = Column(LargeBinary)
    image_id = Column(String, unique=True)
    last_newz = Column(DateTime, default=None, nullable=True)
    last_newz_id = Column(String, default='')
    podcast_files = relationship('PodcastFiles', back_populates='podcast')


# defined table for podcast files with links and all details
class PodcastFiles(Base):
    __tablename__ = 'podcast_files'
    id = Column(Integer, primary_key=True)
    podcast_id = Column(Integer, ForeignKey('rss_podcast.id'))
    podcast = relationship('RssPodcast', back_populates='podcast_files', lazy='joined')
    drive_link = Column(String)
    source_link = Column(String)
    name = Column(String)
    description = Column(String)
    size = Column(String)
    duration = Column(Integer)
    published_date = Column(DateTime)
    is_sent = Column(Integer, default=0)
