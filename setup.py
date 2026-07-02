"""Setup script for AfriHealth Assistant."""

from setuptools import setup, find_packages

setup(
    name="afrihealth-assistant",
    version="0.2.0",
    description="100% offline AI medical assistant for African communities (ADTC 2026 Challenge)",
    packages=find_packages(where="frontend"),
    package_dir={"": "frontend"},
    install_requires=[
        "streamlit",
        "pandas",
        "requests",
        "Pillow",
    ],
    python_requires=">=3.10",
)
