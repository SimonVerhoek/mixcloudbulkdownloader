import threading

from youtube_dl import YoutubeDL


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
