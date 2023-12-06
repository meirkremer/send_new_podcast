from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from time import strftime, gmtime
from typing import List, Type
from premailer import transform
from db_schema import PodcastFiles
from jinja2 import Template


def _create_podcast_box(podcast: Type[PodcastFiles]) -> str:
    """
    Create an HTML representation of a podcast for use in an email template.

    Parameters:
        podcast (Podcast): The Podcast object containing details about the podcast.

    Returns:
        str: The HTML representation of the podcast box.
    """
    # Extract podcast class details
    podcast_details = podcast.podcast

    # Create template of podcast box from template file
    with open('templates/podcast_template.html', 'r', encoding='utf-8') as f:
        podcast_template = Template(f.read())

    # Render the template with podcast details
    podcast_box = podcast_template.render(
        track_link=podcast.drive_link,
        image_link=f'cid:{podcast_details.image_id}',
        podcast_name=podcast_details.title,
        track_name=podcast.name,
        track_description=podcast.description,
        track_duration=strftime('%H:%M:%S', gmtime(podcast.duration)),
        track_size=f"{(int(podcast.size) / 1024**2):.1f} MB",
        track_published=podcast.published_date
    )

    return podcast_box


def _create_html_message(new_podcast: List[Type[PodcastFiles]]) -> str:
    """
    Create an HTML message containing podcast boxes for a list of new podcast files to send it as an email message.

    Parameters:
        new_podcast (list[PodcastFiles]): A list of PodcastFiles objects representing new podcast episodes.

    Returns:
        str: The HTML representation of the email message.
    """

    # Initialize an empty string to concatenate all podcast boxes
    all_podcast_boxes = ''

    # Iterate through each new podcast and create a podcast box
    for podcast in new_podcast:
        all_podcast_boxes += _create_podcast_box(podcast)

    # Create message template from template file
    with open('templates/message_template.html', 'r', encoding='utf-8') as f:
        message_template = Template(f.read())

    # Render the HTML message with all new podcasts and logo area
    email_message = message_template.render(all_boxes=all_podcast_boxes,
                                            logo_link='cid:logo.jpg', subscribe_link='', unsubscribe_link='')
    return email_message


def create_mail_message(new_podcast: List[Type[PodcastFiles]]) -> MIMEMultipart:
    """
    Create an email message with HTML content and embedded images for a list of new podcast files.

    Parameters:
        new_podcast (list[PodcastFiles]): A list of PodcastFiles objects representing new podcast episodes.

    Returns:
        MIMEMultipart: An email message with HTML content and embedded images.
    """

    # Create the HTML content for the email message
    html_message = _create_html_message(new_podcast)

    # Create an MIMEMultipart object to represent the email message
    message = MIMEMultipart()

    # Attach the HTML to the message
    message.attach(MIMEText(transform(html_message), 'html'))

    # Create image objects for each podcast class and attach it to the message
    exist_podcast_id = []
    for podcast in new_podcast:
        if podcast.podcast_id in exist_podcast_id:
            continue
        image_object = MIMEImage(podcast.podcast.image, name=podcast.podcast.image_id, _subtype='jpeg')
        image_object.add_header('Content-ID', f'<{podcast.podcast.image_id}>')
        message.attach(image_object)
        exist_podcast_id.append(podcast.podcast_id)

    # Create an image object for logo and attach it to the message
    with open('templates/freenet.png', 'rb') as f:
        logo = MIMEImage(f.read(), name='logo.jpg')
        logo.add_header('Content-ID', '<logo.jpg>')
        message.attach(logo)

    return message
