#!/usr/bin/env python

from setuptools import setup
from sys import version_info


requirements = [
    'GitPython==2.1.11',
    'boto3==1.7.70',
    'python-magic==0.4.15']

if version_info < (3, 5):
    requirements.append('typing')


setup(
    name='s3git',
    version='0.0.0',
    description='',
    author='NyanKiyoshi',
    author_email='hello@vanille.bid',
    url='https://github.com/NyanKiyoshi/s3git',
    py_modules=['s3git'],
    packages=['s3git'],
    entry_points="""
        [console_scripts]
        s3git-sync=s3git.__main__:main
    """,
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
    ],
    include_package_data=True,
    install_requires=requirements,
    extras_require=dict(
        testing=['pytest']
    )
)
