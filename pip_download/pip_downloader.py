from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Generator, Iterable, List, Optional, Set, Union

from packaging.requirements import Requirement
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.req import InstallRequirement
from pip._vendor.pkg_resources import Requirement as PipRequirement
from piptools._compat import parse_requirements
from piptools.cache import DependencyCache
from piptools.repositories import PyPIRepository
from piptools.resolver import Resolver

from pip_download.utils.download_file import AbcDownloader, DirDownloader, ZipDownloader
from pip_download.utils.wheel import (
    get_supported_platforms,
    get_supported_py_versions,
    is_compatible_wheel,
)

TRequirements = Union[Path, List[str]]


class PipDownloader:
    CACHE_DIR = ".pip-download-cache"

    def __init__(
        self,
        py_versions: Optional[Iterable[str]] = None,
        platforms: Optional[Iterable[str]] = None,
        index_url: Optional[str] = None,
        extra_index_url: Optional[str] = None,
        find_links: Optional[Path] = None,
    ):
        self._py_versions = get_supported_py_versions(py_versions)
        self._platforms = get_supported_platforms(platforms)
        self._repository = self._create_pypi_repository(
            index_url, extra_index_url, find_links
        )

    @classmethod
    def _create_pypi_repository(
        cls,
        index_url: Optional[str],
        extra_index_url: Optional[str],
        find_links: Optional[Path],
    ):
        args = []
        if index_url is not None:
            args.extend(["--index-url", index_url])
        if extra_index_url is not None:
            args.extend(["--extra-index-url", extra_index_url])
        if find_links is not None:
            args.extend(["--find-links", str(find_links)])
        return PyPIRepository(args, cls.CACHE_DIR)

    def _prepare_resolver(self, requirements: TRequirements) -> Resolver:
        if isinstance(requirements, Path):
            constraints = parse_requirements(
                str(requirements),
                self._repository.session,
                self._repository.finder,
                options=self._repository.options,
            )
        else:
            constraints = {
                InstallRequirement(PipRequirement(req), comes_from="line")
                for req in requirements
            }
        cache = DependencyCache(self.CACHE_DIR)

        resolver = Resolver(constraints, self._repository, cache)
        resolver.resolve = partial(resolver.resolve, max_rounds=100)
        return resolver

    def _resolve_requirements(
        self, requirements: TRequirements, pinned: bool = True
    ) -> List[Requirement]:
        resolver = self._prepare_resolver(requirements)
        ireq_set = resolver.resolve()
        if not pinned:
            ireq_set = resolver.constraints
        req_set: Set[Requirement] = {Requirement(str(ireq.req)) for ireq in ireq_set}
        return sorted(req_set, key=lambda req: req.name)

    def resolve_requirements(self, requirements: TRequirements) -> List[Requirement]:
        return self._resolve_requirements(requirements, pinned=True)

    def resolve_requirements_range(
        self, requirements: TRequirements
    ) -> List[Requirement]:
        return self._resolve_requirements(requirements, pinned=False)

    def get_str_requirements(self, requirements: TRequirements) -> str:
        return "\n".join(map(str, self.resolve_requirements(requirements)))

    def get_str_requirements_range(self, requirements: TRequirements) -> str:
        return "\n".join(map(str, self.resolve_requirements_range(requirements)))

    def _download(self, requirements: TRequirements, downloader: AbcDownloader):
        req_lst = self.resolve_requirements(requirements)
        for candidate in self._get_all_candidates(req_lst):
            downloader.download(candidate.link.url, candidate.link.filename)

    def download(self, requirements: TRequirements, dst_dir: Path = Path("dep")):
        with DirDownloader(dst_dir) as downloader:
            self._download(requirements, downloader)

    def save_to_archive(self, requirements: TRequirements, arch_path: Path):
        with ZipDownloader(arch_path) as downloader:
            self._download(requirements, downloader)

    def _get_all_candidates(
        self, req_set: List[Requirement]
    ) -> Generator[InstallationCandidate, None, None]:
        for req in req_set:
            candidates = self._filter_candidates_by_version(
                self._get_all_candidates_for_package(req.name), req
            )
            for candidate in candidates:
                if not candidate.link.is_wheel:
                    yield candidate
                elif is_compatible_wheel(
                    candidate.link.filename, self._py_versions, self._platforms
                ):
                    yield candidate

    @staticmethod
    def _filter_candidates_by_version(
        candidates: Iterable[InstallationCandidate], req: Requirement
    ) -> Generator[InstallationCandidate, None, None]:
        versions = set(req.specifier.filter(str(c.version) for c in candidates))
        return (c for c in candidates if str(c.version) in versions)

    @contextmanager
    def _allow_all_wheels(self):
        with self._repository.allow_all_wheels():
            try:
                self._repository.finder.find_all_candidates.cache_clear()
                yield
            finally:
                self._repository.finder.find_all_candidates.cache_clear()

    def _get_all_candidates_for_package(self, name: str) -> List[InstallationCandidate]:
        with self._allow_all_wheels():
            return self._repository.find_all_candidates(name)
