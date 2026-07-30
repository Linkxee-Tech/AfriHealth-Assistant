"""Setup script for AfriHealth Assistant."""

from setuptools import setup, find_packages

setup(
    name="afrihealth-assistant",
    version="0.2.0",
    description="100% offline AI medical assistant for African communities (ADTC 2026 Challenge)",
    packages=find_packages(include=["backend*", "frontend*", "knowledge_base*"] ),
    install_requires=[
        "fastapi>=0.115,<1",
        "uvicorn[standard]>=0.30,<1",
        "streamlit>=1.40,<2",
        "starlette>=0.40,<0.47",
        "sqlalchemy>=2,<3",
        "pydantic>=2.12,<3",
        "pydantic-settings>=2.10,<3",
        "python-multipart>=0.0.10",
        "python-dotenv>=1,<2",
        "requests>=2.27,<3",
        "pandas>=1.5,<3",
        "Pillow>=9.5,<13",
        "psutil>=5.9,<8",
        "reportlab>=4,<5",
    ],
    python_requires=">=3.10",
)
