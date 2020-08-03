import sys
from typing import Iterable, Set

from packaging.tags import sys_tags
from pip._internal.models.wheel import Wheel


def is_compatible_wheel(
    file_name: str, py_versions: Set[str], platforms: Set[str]
) -> bool:
    wheel = Wheel(file_name)
    return is_compatible_py_version(wheel, py_versions) and is_compatible_platform(
        wheel, platforms
    )


def is_compatible_py_version(wheel: Wheel, py_versions: Set[str]) -> bool:
    return bool(set(wheel.pyversions) & py_versions)


def is_compatible_platform(wheel: Wheel, platforms: Set[str]) -> bool:
    for wheel_plat in wheel.plats:
        for supported_plat in platforms:
            if supported_plat in wheel_plat or wheel_plat == "any":
                return True
    return False


def get_supported_platforms(platforms: Iterable[str]) -> Set[str]:
    if not platforms:
        platforms = {t.platform for t in sys_tags()}
    else:
        platforms = set(platforms)
    return platforms


def get_supported_py_versions(py_versions: Iterable[str]) -> Set[str]:
    if not py_versions:
        py_versions = {f"cp{sys.version_info.major}{sys.version_info.minor}"}
    else:
        py_versions = set(py_versions)

    for py_version in py_versions.copy():
        if py_version.startswith("cp"):
            py_num = py_version[2:]
            py_versions |= {f"py{py_num}", f"py{py_num[0]}"}
    return py_versions
