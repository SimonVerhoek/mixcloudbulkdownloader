import threading

from youtube_dl import YoutubeDL
from PySide2.QtWidgets import QTreeWidget

from .data_classes import Cloudcast, MixcloudUser
from .api import get_mixcloud_API_data, user_cloudcasts_API_url
from .custom_widgets.cloudcast_q_tree_widget_item import CloudcastQTreeWidgetItem


class DownloadThread(threading.Thread):
    def __init__(self, item, download_dir):
        threading.Thread.__init__(self)
        self.item = item
        self.urls = [item.cloudcast.url]
        self.download_dir = download_dir

    def track_progress(self, d):
        if d['status'] == 'downloading':
            progress = (
                f"{d['_percent_str']} of {d['_total_bytes_str']} at {d['_speed_str']}"
            )
            self.item.update_download_progress(progress=progress)
        if d['status'] == 'finished':
            self.item.update_download_progress(progress='Done!')

    def run(self) -> None:
        ydl_opts = {
            'outtmpl': f'{self.download_dir}/%(title)s.%(ext)s',
            'progress_hooks': [self.track_progress],
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download(self.urls)

        return


class GetCloudcastsThread(threading.Thread):
    def __init__(self, cloudcasts_list: QTreeWidget, user: MixcloudUser):
        threading.Thread.__init__(self)

        self.cloudcasts_list = cloudcasts_list
        self.user = user

    def _query_cloudcasts(self, user: MixcloudUser, url: str = ''):
        if not url:
            url = user_cloudcasts_API_url(username=user.username)

        response = get_mixcloud_API_data(url=url)

        for cloudcast in response['data']:
            cloudcast = Cloudcast(
                name=cloudcast['name'], url=cloudcast['url'], user=user,
            )
            item = CloudcastQTreeWidgetItem(cloudcast=cloudcast)
            self.cloudcasts_list.addTopLevelItem(item)

        if response.get('paging') and response['paging'].get('next'):
            next_url = response['paging'].get('next')
            self._query_cloudcasts(user=user, url=next_url)

    def run(self) -> None:
        self._query_cloudcasts(user=self.user)
        return
