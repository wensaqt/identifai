import sys
from pathlib import Path

import pytest
from faker import Faker

# Allow importing backend modules without doctr installed
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


@pytest.fixture
def fake():
    Faker.seed(42)
    return Faker("fr_FR")
