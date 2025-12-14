from setuptools import setup

setup(
    name='src2file',
    version='0.1.0',
    description='A CLI tool to flatten source code into a single text file for LLM context (ChatGPT, Claude, etc).',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='levmv',
    url='https://github.com/levmv/src2file',
    py_modules=['src2file'],
    entry_points={
        'console_scripts': [
            'src2file=src2file:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Utilities',
        'Topic :: Software Development',
    ],
    python_requires='>=3.6',
)