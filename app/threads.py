import threading

from PySide2.QtCore import QThread, Signal
from PySide2.QtWidgets import QTreeWidget
from youtube_dl import YoutubeDL

from .api import get_mixcloud_API_data, search_user_API_url, user_cloudcasts_API_url
from .custom_widgets.cloudcast_q_tree_widget_item import CloudcastQTreeWidgetItem
from .data_classes import Cloudcast, MixcloudUser
from .logging import logging


logger = logging.getLogger(__name__)


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


class GetCloudcastsThread(QThread):
    error_signal = Signal(object)

    def __init__(self, cloudcasts_list: QTreeWidget):
        super().__init__()

        self.cloudcasts_list = cloudcasts_list

    def _query_cloudcasts(self, user: MixcloudUser, url: str = ''):
        if not url:
            url = user_cloudcasts_API_url(username=user.username)

        response, error = get_mixcloud_API_data(url=url)
        if error:
            self.error_signal.emit(error)
            self.stop()
        else:
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
        logger.debug('get_cloudcasts_thread started')
        while not self.isInterruptionRequested():
            if not self.user:
                error_msg = 'no user provided'
                logger.error(error_msg)
                self.error_signal.emit(error_msg)

            self._query_cloudcasts(user=self.user)
            return

    def stop(self):
        logger.debug("Thread Stopped")
        self.requestInterruption()
        self.wait()


class SearchArtistThread(QThread):
    error_signal = Signal(object)
    new_result = Signal(MixcloudUser)

    phrase: str = ''

    def show_suggestions(self, phrase: str) -> None:
        url = search_user_API_url(phrase=phrase)
        response, error = get_mixcloud_API_data(url=url)
        if error:
            self.error_signal.emit(error)
            self.stop()
        else:
            for i, result in enumerate(response['data']):
                user = MixcloudUser(**result)
                self.new_result.emit(user)

    def run(self) -> None:
        logger.debug('thread started')
        while not self.isInterruptionRequested():
            if not self.phrase:
                error_msg = 'no search phrase provided'
                logger.error(error_msg)
                self.error_signal.emit(error_msg)

            self.show_suggestions(phrase=self.phrase)
            return

    def stop(self):
        logger.debug("thread Stopped")
        self.requestInterruption()
        self.wait()
