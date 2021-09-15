#!/usr/bin/env python

import utoken
from pathlib import Path

from setuptools import setup, find_namespace_packages

long_description = Path('README.md').read_text(encoding='utf-8', errors='ignore')

classifiers = [  # copied from https://pypi.org/classifiers/
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'Topic :: Utilities',
    'Topic :: Text Processing',
    'Topic :: Text Processing :: General',
    'Topic :: Text Processing :: Filters',
    'Topic :: Text Processing :: Linguistic',
    'License :: OSI Approved :: Apache Software License',
    'Programming Language :: Python :: 3 :: Only',
]

setup(
    name='utoken',
    version=utoken.__version__,
    description=utoken.__description__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=classifiers,
    python_requires='>=3.8',
    url='https://github.com/uhermjakob/utoken',
    download_url='https://github.com/uhermjakob/utoken',
    platforms=['any'],
    author='Ulf Hermjakob',
    author_email='ulf@isi.edu',
    packages=find_namespace_packages(exclude=['aux']),
    keywords=['machine translation', 'datasets', 'NLP', 'natural language processing,'
                                                        'computational linguistics'],
    entry_points={
        'console_scripts': [
            'utokenize=utoken.utokenize:main',
            'detokenize=utoken.detokenize:main'
        ],
    },
    install_requires=[
        'regex==2021.8.3',
    ],
    include_package_data=True,
    zip_safe=False,
)
