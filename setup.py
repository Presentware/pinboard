from setuptools import setup

with open('README.md') as readme_file:
    description = readme_file.read()

setup(
    name = 'Pinboard',
    version = '0.1.3',
    description = 'Make virtual interactive pinboards easily',
    author = 'Presentware',
    license = 'Public Domain',
    py_modules = ['pinboard'],
    package_dir = {'': 'src'},
    classifiers = [
        'Programming Language :: Python :: 3',
        'Development Status :: 4 - Beta',
        'License :: Public Domain',
        'Operating System :: OS Independent',
    ],
    long_description = description,
    long_description_content_type = 'text/markdown',
)
