from pathlib import Path
from typing import Optional, Iterable

import click

from .pip_download import PipDownloaderConfig, PyVersionEnum
from .pip_download import PipDownloader


@click.command()
@click.argument('requirement', required=False)
@click.option(
    '-r',
    '--requirements',
    'requirements_file',
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    '--dst-dir',
    type=click.Path(file_okay=False),
    default=Path('.'),
    show_default=True,
)
@click.option('--to-archive', type=click.Path(dir_okay=False, exists=False))
@click.option(
    'platforms',
    '--platform',
    default=['win'],
    type=click.Choice(['win', 'linux']),
    multiple=True,
    show_default=True,
)
@click.option(
    'py_versions',
    '--py-version',
    default=['cp37'],
    type=click.Choice(PyVersionEnum.all_versions()),
    multiple=True,
    show_default=True,
)
@click.option('-i', '--index-url')
@click.option('--extra-index-url')
@click.option('-f', '--find-links', type=click.Path(exists=True, file_okay=False))
@click.option('--dry-run', is_flag=True)
@click.option('--requirements-range', is_flag=True)
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
        # todo show help, create Option required on of the
        raise Exception('You have to specify requirements or requirements file')

    if requirement and requirements_file:
        # todo show help
        raise Exception('Only requirement or requirements file')

    config = PipDownloaderConfig(
        dst_dir=dst_dir,
        to_archive=to_archive,
        dry_run=dry_run,
        required_platforms=platforms,
        required_py_versions=py_versions,
        index_url=index_url,
        extra_index_url=extra_index_url,
        find_links=find_links,
    )
    downloader = PipDownloader(config)

    if requirements_range and not dry_run:
        raise Exception  # todo create Option required if `dry_run`

    if requirement:
        install_requirements = downloader.parse_requirement_by_str(requirement)
    else:
        install_requirements = downloader.parse_requirement_from_file(requirements_file)

    if dry_run:
        if requirements_range:
            downloader.resolve_range_dependencies(install_requirements)
        else:
            downloader.resolve_dependencies(install_requirements)
    else:
        downloader.download(install_requirements)


if __name__ == '__main__':
    cli()
