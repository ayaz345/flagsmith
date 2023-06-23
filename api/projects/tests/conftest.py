import pytest

from segments.models import Segment


@pytest.fixture()
def segments(project):
    return [
        Segment.objects.create(name=f"Test Segment {i}", project=project)
        for i in range(3)
    ]
