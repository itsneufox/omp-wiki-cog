from setuptools import setup, find_packages

setup(
    name="omp-wiki-cog",
    version="1.0.0",
    description="A Red bot cog for searching open.mp documentation",
    author="itsneufox",
    author_email="your.email@example.com",
    url="https://github.com/itsneufox/omp-wiki-cog",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.8.0",
        "beautifulsoup4>=4.11.0",
        "lxml>=4.9.0",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)
