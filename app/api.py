from typing import Dict, Tuple

import requests
import yt_dlp

# from .logging import logging


# logger = logging.getLogger(__name__)

MIXCLOUD_API_URL = 'https://api.mixcloud.com'


def search_user_API_url(phrase: str):
    return f'{MIXCLOUD_API_URL}/search/?q={phrase}&type=user'


def user_cloudcasts_API_url(username: str):
    return f'{MIXCLOUD_API_URL}/{username}/cloudcasts/'


def get_mixcloud_API_data(url: str) -> Tuple[Dict, str]:
    response = None
    error = ''
    try:
        req = requests.get(url=url)
        response = req.json()
    except requests.exceptions.RequestException as e:
        error = 'Failed to query Mixcloud API'
        # logger.error(msg=f'{error}: {e}', exc_info=True)

    if 'error' in response:
        error_type = response['error']['type']
        error_msg = response['error']['message']
        error = f'{error_type}: {error_msg}'
        # logger.error(msg=error, exc_info=True)

    return response, error


def download_cloudcasts(urls, download_dir):
    ydl_opts = {'outtmpl': f'{download_dir}/%(title)s.%(ext)s'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(urls)
