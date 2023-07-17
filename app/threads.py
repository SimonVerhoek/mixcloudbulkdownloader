from typing import List

from PySide6.QtCore import QThread, Signal
from youtube_dl import YoutubeDL

from .api import get_mixcloud_API_data, search_user_API_url, user_cloudcasts_API_url
from .data_classes import Cloudcast, MixcloudUser


# from .logging import logging


# logger = logging.getLogger(__name__)


class DownloadThread(QThread):
    urls: List[str] = []
    download_dir: str = None

    progress_signal = Signal(str, str)
    interrupt_signal = Signal()
    error_signal = Signal(object)

    def _track_progress(self, d):
        item_name = (
            d['filename']
            .replace(f'{self.download_dir}/', '')
            .replace('.m4a', '')
            .replace('_', '/')
        )

        progress = 'unknown'
        if d['status'] == 'downloading':
            progress = (
                f"{d['_percent_str']} of {d['_total_bytes_str']} at {d['_speed_str']}"
            )
        elif d['status'] == 'finished':
            progress = 'Done!'

        self.progress_signal.emit(item_name, progress)

    def run(self) -> None:
        if not self.download_dir:
            error_msg = 'no download directory provided'
            self.error_signal.emit(error_msg)
            return

        ydl_opts = {
            'outtmpl': f'{self.download_dir}/%(uploader)s - %(title)s.%(ext)s',
            'progress_hooks': [self._track_progress],
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download(self.urls)

        return

    def stop(self):
        self.terminate()
        self.interrupt_signal.emit()
        self.wait()


class GetCloudcastsThread(QThread):
    error_signal = Signal(object)
    interrupt_signal = Signal()
    new_result = Signal(Cloudcast)

    user: MixcloudUser = None

    def _query_cloudcasts(self, user: MixcloudUser, url: str = ''):
        if not url:
            url = user_cloudcasts_API_url(username=user.username)

        response, error = get_mixcloud_API_data(url=url)
        if error:
            self.error_signal.emit(error)
            self.stop()
            return

        while not self.isInterruptionRequested():
            for cloudcast in response['data']:
                cloudcast = Cloudcast(
                    name=cloudcast['name'], url=cloudcast['url'], user=user,
                )
                self.new_result.emit(cloudcast)

            if response.get('paging') and response['paging'].get('next'):
                next_url = response['paging'].get('next')
                self._query_cloudcasts(user=user, url=next_url)
            return

    def run(self) -> None:
        # logger.debug('get_cloudcasts_thread started')
        if not self.user:
            error_msg = 'no user provided'
            # logger.error(error_msg)
            self.error_signal.emit(error_msg)

        self._query_cloudcasts(user=self.user)
        return

    def stop(self):
        # logger.debug("Thread Stopped")
        self.requestInterruption()
        self.interrupt_signal.emit()
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
        # logger.debug('thread started')
        while not self.isInterruptionRequested():
            if not self.phrase:
                error_msg = 'no search phrase provided'
                # logger.error(error_msg)
                self.error_signal.emit(error_msg)

            self.show_suggestions(phrase=self.phrase)
            return

    def stop(self):
        # logger.debug("thread Stopped")
        self.requestInterruption()
        self.wait()
