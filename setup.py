from setuptools import setup, find_packages

setup(
    name="ai_bot_fastapi",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic"
    ]
)
