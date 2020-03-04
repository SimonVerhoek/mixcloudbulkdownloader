MIXCLOUD_API_URL = 'https://api.mixcloud.com'


def search_user_API_url(phrase: str):
    return f'{MIXCLOUD_API_URL}/search/?q={phrase}&type=user'


def user_cloudcasts_API_url(username: str):
    return f'{MIXCLOUD_API_URL}/{username}/cloudcasts/'
