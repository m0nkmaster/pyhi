import os
import sys
import pytest

# Get the absolute path of the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the project root directory to the Python path
sys.path.insert(0, project_root)

# Configure pytest-asyncio default loop scope
def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function"
