from setuptools import find_packages, setup

from civet import __version__

setup(
    name='civet',
    version=__version__,
    author='Counsyl',
    author_email='opensource@counsyl.com',
    license='Apache License 2.0',
    description='CoffeeScript and Sass asset precompiler for the Django',
    long_description=open('README.md', 'r').read(),
    url='https://github.com/counsyl/civet',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "Django>=1.3",
        "watchdog>=0.7.1"
    ],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Pre-processors',
    ],
    zip_safe=False,
)
