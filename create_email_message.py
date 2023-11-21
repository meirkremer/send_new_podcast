from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from time import strftime, gmtime

from premailer import transform
from db_schema import PodcastFiles
from jinja2 import Template


def create_podcast_box(podcast):
    podcast_details = podcast.podcast
    with open('templates/podcast_template.html', 'r', encoding='utf-8') as f:
        podcast_template = Template(f.read())
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


def create_html_message(new_podcast: list[PodcastFiles]):
    all_podcast_boxes = ''
    for podcast in new_podcast:
        all_podcast_boxes += create_podcast_box(podcast)

    with open('templates/message_template.html', 'r', encoding='utf-8') as f:
        message_template = Template(f.read())

    email_message = message_template.render(all_boxes=all_podcast_boxes,
                                            logo_link='cid:logo.jpg', subscribe_link='', unsubscribe_link='')
    return email_message


def create_mail_message(new_podcast: list[PodcastFiles]):
    html_message = create_html_message(new_podcast)
    message = MIMEMultipart()
    message.attach(MIMEText(transform(html_message), 'html'))

    exist_podcast_id = []
    for podcast in new_podcast:
        if podcast.podcast_id in exist_podcast_id:
            continue
        image_object = MIMEImage(podcast.podcast.image, name=podcast.podcast.image_id)
        image_object.add_header('Content-ID', f'<{podcast.podcast.image_id}>')
        message.attach(image_object)
        exist_podcast_id.append(podcast.podcast_id)

    with open('templates/freenet.png', 'rb') as f:
        logo = MIMEImage(f.read(), name='logo.jpg')
        logo.add_header('Content-ID', '<logo.jpg>')
        message.attach(logo)

    return message
