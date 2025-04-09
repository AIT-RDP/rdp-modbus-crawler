#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

setup(
    name='modbus_crawler',
    version='2025.1.1',
    description="Generic Modbus Crawler which reads, writes and decodes Modbus registers according to csv-register spec",
    long_description=readme + '\r\n',
    author="Christan Seitl",
    author_email='christian.seitl@ait.ac.at',
    url='https://gitlab-intern.ait.ac.at/ees-lachs/modbus-crawler',
    packages=find_packages(exclude=['contrib', 'docs', 'test', 'tests*']),
    package_dir={'modbus_crawler': 'modbus_crawler'},
    include_package_data=True,
    install_requires=[
        'pymodbus==3.8.3', 'schedule'
    ],
    extras_require={
        'test': [
            'pytest',
            'pytest-asyncio',
            'twisted'
        ]
    },
    zip_safe=False,
    keywords=['Modbus', 'Crawler'],
    python_requires='>=3.10',
)
