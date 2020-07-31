import abc
import zipfile
from pathlib import Path
from urllib.request import urlopen

from tqdm import tqdm


def download_file(url: str, file_name: str) -> bytes:
    resp = urlopen(url)
    total_size = int(resp.headers.get("content-length", 0))
    data = b""
    block_sz = 8192
    with tqdm(
        unit="B", unit_scale=True, miniters=1, desc=file_name, total=total_size
    ) as bar:
        while True:
            buffer = resp.read(block_sz)
            if not buffer:
                break
            data += buffer
            bar.update(block_sz)
    return data


class AbcDownloader(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def download(self, url: str, file_name: str):
        raise NotImplementedError

    @abc.abstractmethod
    def __enter__(self):
        raise NotImplementedError

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        raise NotImplementedError


class DirDownloader(AbcDownloader):
    def __init__(self, dst_dir: Path):
        dst_dir.mkdir(exist_ok=True)
        self._dst_dir = dst_dir

    def download(self, url: str, file_name: str):
        file_path = self._dst_dir / file_name
        with file_path.open("wb") as f:
            f.write(download_file(url, file_name))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class ZipDownloader(AbcDownloader):
    def __init__(self, zip_path: Path):
        self._zip_path = zip_path

    def __enter__(self):
        self._zip_file = zipfile.ZipFile(self._zip_path, "w")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._zip_file.close()
        return False

    def download(self, url: str, file_name: str):
        self._zip_file.writestr(file_name, download_file(url, file_name))
