# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='obal',
    version='0.0.1',
    description='packaging wrapper using ansible',
    long_description=long_description,
    url='https://github.com/theforeman/obal',
    author='The Foreman Project',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: GPLv2',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='ansible foreman packaging koji brew mock',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    install_requires=['ansible'],

    extras_require={
        'argcomplete': ['argcomplete'],
    },

    package_data={  # Optional
        'obal': ['*.yml'],
    },

    entry_points={
        'console_scripts': [
            'obal=obal:main',
        ],
    },
)
