from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.request import urlretrieve

from tqdm import tqdm


class TqdmUpTo(tqdm):
    """Provides `update_to(n)` which uses `tqdm.update(delta_n)`."""
    def update_to(self, b=1, bsize=1, tsize=None):
        """
        b  : int, optional
            Number of blocks transferred so far [default: 1].
        bsize  : int, optional
            Size of each block (in tqdm units) [default: 1].
        tsize  : int, optional
            Total size (in tqdm units). If [default: None] remains unchanged.
        """
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)  # will also set self.n = b * bsize


def download_file(url: str, dst_dir: Path, file_name: Optional[str] = None) -> None:
    if file_name is None:
        file_name = Path(urlparse(url).path).name
    file_path = dst_dir / file_name

    with TqdmUpTo(
            unit='B',
            unit_scale=True,
            miniters=1,
            desc=file_name,
    ) as t:  # all optional kwargs
        urlretrieve(url, file_path, reporthook=t.update_to)
