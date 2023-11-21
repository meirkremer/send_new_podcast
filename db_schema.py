from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Integer, LargeBinary, DateTime, ForeignKey

Base = declarative_base()


class Subscribers(Base):
    """
    Table to store information about podcast subscribers.

    Attributes:
    - id (int): Primary key for the table.
    - name (str): Name of the subscriber.
    - email (str): Email address of the subscriber (unique).
    """
    __tablename__ = 'subscribers'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    email = Column(String, unique=True)


class RssPodcast(Base):
    """
    Table to store information about podcast with RSS links.

    Attributes:
    - id (int): Primary key for the table.
    - rss_link (str): RSS link for the podcast (unique).
    - e_tag (str): ETag for the RSS link (default is an empty string).
    - title (str): Title of the podcast.
    - description (str): Description of the podcast.
    - image (LargeBinary): Binary data for the podcast image.
    - image_id (str): Image ID for the podcast (unique).
    - last_newz (DateTime): Date and time of the last news update (default is None).
    - last_newz_id (str): ID of the last entry (default is an empty string).
    - podcast_files (relationship): Relationship with PodcastFiles table.
    """
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


class PodcastFiles(Base):
    """
    Table to store information about podcast files with links and details.

    Attributes:
    - id (int): Primary key for the table.
    - podcast_id (int): Foreign key referencing the RssPodcast table.
    - podcast (relationship): Relationship with RssPodcast table.
    - drive_link (str): Link to the podcast file on the GooglDrive.
    - source_link (str): Source link for the podcast file.
    - name (str): Name of the podcast file.
    - description (str): Description of the podcast file.
    - size (str): Size of the podcast file.
    - duration (int): Duration in seconds of the podcast file.
    - published_date (DateTime): Date and time when the podcast file was published.
    - is_sent (int): Flag indicating whether the podcast file has been sent (default is 0 - False).
    """
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
