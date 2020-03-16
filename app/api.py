import requests
from youtube_dl import YoutubeDL


MIXCLOUD_API_URL = 'https://api.mixcloud.com'


def search_user_API_url(phrase: str):
    return f'{MIXCLOUD_API_URL}/search/?q={phrase}&type=user'


def user_cloudcasts_API_url(username: str):
    return f'{MIXCLOUD_API_URL}/{username}/cloudcasts/'


def get_mixcloud_API_data(url: str):
    req = requests.get(url=url)
    response = req.json()
    return response


def download_cloudcasts(urls, download_dir):
    ydl_opts = {'outtmpl': f'{download_dir}/%(title)s.%(ext)s'}
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download(urls)
