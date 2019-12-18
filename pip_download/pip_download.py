import itertools
import re
from enum import Enum
from operator import attrgetter
from pathlib import Path
from typing import List, Set, Iterator, Generator, Optional, Tuple

from pip._internal.models.candidate import InstallationCandidate
from pip._internal.req import parse_requirements, InstallRequirement
from pip._internal.wheel import Wheel
from pip._vendor.packaging.requirements import Requirement
from piptools.repositories import PyPIRepository
from piptools.resolver import Resolver
from pydantic import BaseModel, HttpUrl, AnyUrl

from .download_file import download_file


class PlatformEnum(Enum):
    ANY = 'any'
    ANY_LINUX = 'linux'
    ANY_WIN = 'win'
    OTHER = 'other'

    @classmethod
    def from_platform_name(cls, platform_name: str) -> 'PlatformEnum':
        if platform_name == 'any':
            return cls.ANY
        elif 'linux' in platform_name:
            return cls.ANY_LINUX
        elif 'win' in platform_name:
            return cls.ANY_WIN
        else:
            return cls.OTHER

    @classmethod
    def _missing_(cls, value) -> 'PlatformEnum':
        return cls.from_platform_name(value)


class PyVersionEnum(Enum):
    CP27 = 'cp27'
    CP33 = 'cp33'
    CP34 = 'cp34'
    CP35 = 'cp35'
    CP36 = 'cp36'
    CP37 = 'cp37'
    CP38 = 'cp38'

    def is_compatible(self, version: str) -> bool:
        if version.lower() == self.value:
            return True

        if re.search(r'py\d', version.lower()) and version[2] == self.value[2]:
            return True

        return False

    def __str__(self):
        return f'{self.value}'

    @classmethod
    def all_versions(cls) -> List[str]:
        return list(map(str, cls))


class PipDownloaderConfig(BaseModel):
    dst_dir: Path = Path('.')
    platforms: Set[PlatformEnum] = {PlatformEnum.ANY_WIN}
    py_versions: Set[PyVersionEnum] = {PyVersionEnum.CP37}
    download_sources: bool = True
    download_wheels: bool = True
    index_url: Optional[HttpUrl]
    extra_index_url: Optional[HttpUrl]
    find_links: Optional[Path]


class PipDownloader:
    def __init__(self, config: PipDownloaderConfig):
        self._conf: PipDownloaderConfig = config.copy()
        self._repository = PyPIRepository(self._pip_args)

    @property
    def _pip_args(self):
        args = []
        if self._conf.index_url is not None:
            args.extend(['--index-url', str(self._conf.index_url)])
        if self._conf.extra_index_url is not None:
            args.extend(['--extra-index-url', str(self._conf.extra_index_url)])
        if self._conf.find_links is not None:
            args.extend(['--find-links', str(self._conf.find_links)])

        return args

    def download(self, constraints: Iterator[InstallRequirement]):
        requirements_set = self.resolve_dependencies(constraints)
        all_candidates = itertools.chain.from_iterable(
            map(self._get_suitable_candidates, requirements_set)
        )
        self._conf.dst_dir.mkdir(exist_ok=True)
        self._download_candidates(all_candidates)

    def _get_suitable_candidates(
            self, req: InstallRequirement
    ) -> Generator[InstallationCandidate, None, None]:
        """Get candidates for requirement."""
        all_candidates = self._get_all_candidates(req.name)
        candidates = self._filter_candidates_by_req(all_candidates, req)

        for candidate in candidates:
            if not candidate.link.is_wheel and self._conf.download_sources:
                yield candidate
            elif (
                    candidate.link.is_wheel
                    and self._conf.download_wheels
                    and self._is_compatible_wheel(candidate)
            ):
                yield candidate

    def _is_compatible_wheel(self, candidate: InstallationCandidate) -> bool:
        wheel = Wheel(candidate.link.filename)

        return (
                self._is_compatible_py_version(wheel)
                and self._is_compatible_platform(wheel)
        )

    def _is_compatible_py_version(self, wheel: Wheel) -> bool:
        for version in wheel.pyversions:
            for required_version in self._conf.py_versions:
                if required_version.is_compatible(version):
                    return True

        return False

    def _is_compatible_platform(self, wheel: Wheel) -> bool:
        wheel_platforms = set(map(PlatformEnum.from_platform_name, wheel.plats))
        if PlatformEnum.ANY in (self._conf.platforms.union(wheel_platforms)):
            return True

        return bool(wheel_platforms.intersection(self._conf.platforms))

    def _download_candidates(self, candidates: Iterator[InstallationCandidate]) -> None:
        for candidate in candidates:
            download_file(
                candidate.link.url, self._conf.dst_dir, candidate.link.filename
            )

    def _resolve_dependencies(
            self, constraints: Iterator[InstallRequirement]
    ) -> Tuple[Set[InstallRequirement], Set[InstallRequirement]]:
        resolver = Resolver(constraints, self._repository)
        best_match_req_set = resolver.resolve()
        range_req_set = resolver.constraints

        return best_match_req_set, range_req_set

    @staticmethod
    def _get_download_dependencies_message(req_set: Set[InstallRequirement]) -> str:
        return '\n'.join(map(str, sorted(req_set, key=attrgetter('name'))))

    def resolve_dependencies(
            self, constraints: Iterator[InstallRequirement]
    ) -> Set[InstallRequirement]:
        req_set, _ = self._resolve_dependencies(constraints)
        print(self._get_download_dependencies_message(req_set))
        return req_set

    def resolve_range_dependencies(
            self, constraints: Iterator[InstallRequirement]
    ) -> Set[InstallRequirement]:
        _, req_set = self._resolve_dependencies(constraints)
        print(self._get_download_dependencies_message(req_set))
        return req_set

    def _get_all_candidates(self, name: str) -> List[InstallationCandidate]:
        with self._repository.allow_all_wheels():
            return self._repository.find_all_candidates(name)

    @staticmethod
    def _filter_candidates_by_req(
            candidates: Iterator[InstallationCandidate], req: InstallRequirement
    ) -> Generator[InstallationCandidate, None, None]:
        compatible_versions = set(
            req.specifier.filter(str(c.version) for c in candidates)
        )
        return (c for c in candidates if str(c.version) in compatible_versions)

    def parse_requirement_by_str(
            self, requirements_str: str
    ) -> Iterator[InstallRequirement]:
        return (
            InstallRequirement(Requirement(requirement_str), comes_from='input')
            for requirement_str in requirements_str.splitlines()
        )

    def parse_requirement_from_file(
            self, requirement_path: Path
    ) -> Iterator[InstallRequirement]:
        return parse_requirements(
            str(requirement_path),
            finder=self._repository.finder,
            session=self._repository.session,
            options=self._repository.options,
        )
