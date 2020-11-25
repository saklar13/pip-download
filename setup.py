from setuptools import find_packages, setup


def read_file(file_name):
    with open(file_name) as f:
        return f.read().strip()


setup(
    name="pip-download",
    version=read_file("version.txt"),
    description="downloads python packages for specified platform and python version",
    author="Kyrylo Maksymenko",
    author_email="saklar13@gmail.com",
    url="https://github.com/saklar13/pip-download",
    packages=find_packages(),
    entry_points={"console_scripts": ["pip-download = pip_download.cli:cli"]},
    include_package_data=True,
    install_requires=[
        "click~=7.1",
        "pip-tools~=5.4",
        "pip>=20.1,<20.4",
        "tqdm~=4.53",
        "packaging~=20.4",
    ],
    python_requires="~=3.7",
)
