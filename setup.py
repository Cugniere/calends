"""Setup configuration for Calends."""

from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of README file
current_directory = Path(__file__).parent
long_description = (current_directory / "README.md").read_text(encoding="utf-8")

setup(
    name="calends",
    version="0.1.0",
    description="A minimalist terminal calendar that displays your iCal events in a clean weekly view",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Cugniere",
    url="https://github.com/cugniere/calends",
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*"]),
    python_requires=">=3.10",
    install_requires=[
        # No external runtime dependencies - uses only Python stdlib
    ],
    extras_require={
        "dev": [
            "black>=25.9.0",
            "pytest>=8.4.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "calends=calends.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Utilities",
    ],
    keywords="calendar ical terminal cli ics",
    project_urls={
        "Homepage": "https://github.com/cugniere/calends",
        "Repository": "https://github.com/cugniere/calends",
        "Issues": "https://github.com/cugniere/calends/issues",
    },
)
