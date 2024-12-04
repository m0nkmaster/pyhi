from setuptools import setup, find_namespace_packages

setup(
    name="voice-assistant",
    version="0.1.0",
    packages=find_namespace_packages(include=["src*"]),
    package_dir={"": "."},
    install_requires=[
        "openai>=1.56.1",
        "python-dotenv>=0.19.0",
        "pyaudio>=0.2.11",
        "numpy>=1.21.0",
    ],
    extras_require={
        "test": [
            "pytest>=6.2.5",
            "pytest-mock>=3.6.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "voice-assistant=src.app:main",
        ],
    },
    python_requires=">=3.9",
) 