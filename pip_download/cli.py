from pathlib import Path
from typing import Iterable, Optional

import click
from pkg_resources import get_distribution

from pip_download.pip_downloader import PipDownloader
from pip_download.utils.cli_helpers import PathPath

version = get_distribution("pip-download").version


@click.command()
@click.argument("requirement", required=False)
@click.option(
    "-r",
    "--requirements",
    "requirements_file",
    type=PathPath(exists=True, dir_okay=False),
)
@click.option(
    "-d",
    "--dst-dir",
    type=PathPath(file_okay=False),
    default=Path("."),
    show_default=True,
)
@click.option("--to-archive", type=PathPath(dir_okay=False, exists=False))
@click.option(
    "platforms",
    "-p",
    "--platform",
    default=["win32"],
    multiple=True,
    show_default=True,
)
@click.option(
    "py_versions",
    "-py",
    "--py-version",
    default=["cp37"],
    multiple=True,
    show_default=True,
)
@click.option("-i", "--index-url")
@click.option("--extra-index-url")
@click.option("-f", "--find-links", type=PathPath(exists=True, file_okay=False))
@click.option("--dry-run", is_flag=True)
@click.option("--requirements-range", is_flag=True)
@click.version_option(version, message="pip-download, version %(version)s")
def cli(
    requirement: Optional[str],
    requirements_file: Optional[Path],
    dst_dir: Path,
    to_archive: Optional[Path],
    platforms: Iterable[str],
    py_versions: Iterable[str],
    index_url: Optional[str],
    extra_index_url: Optional[str],
    find_links: Optional[str],
    dry_run: bool,
    requirements_range: bool,
):
    if not requirement and not requirements_file:
        # todo show help, create Option required one of the
        raise Exception("You have to specify requirements or requirements file")

    if requirement and requirements_file:
        # todo show help
        raise Exception("Only requirement or requirements file")

    if requirements_range and not dry_run:
        raise Exception  # todo create Option required if `dry_run`

    downloader = PipDownloader(
        py_versions, platforms, index_url, extra_index_url, find_links
    )

    requirements = requirement if requirement else requirements_file
    if dry_run and requirements_range:
        click.echo(downloader.get_str_requirements_range(requirements))
    elif dry_run and not requirements_range:
        click.echo(downloader.get_str_requirements(requirements))
    elif to_archive:
        downloader.save_to_archive(requirements, to_archive)
    else:
        downloader.download(requirements, dst_dir)


if __name__ == "__main__":
    cli()
