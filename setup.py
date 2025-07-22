from setuptools import setup, find_packages

setup(
    name="secretgarden",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "paho-mqtt>=1.6.1",
        "pymodbus>=3.5.4",
        "pyserial>=3.5",
    ],
) 