import threading

from youtube_dl import YoutubeDL


class DownloadThread(threading.Thread):
    def __init__(self, urls, download_dir):
        threading.Thread.__init__(self)
        self.urls = urls
        self.download_dir = download_dir

    def run(self) -> None:
        ydl_opts = {'outtmpl': f'{self.download_dir}/%(title)s.%(ext)s'}
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download(self.urls)

        return
