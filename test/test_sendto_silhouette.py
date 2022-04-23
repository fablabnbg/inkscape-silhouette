try:
    from pathlib import Path
except ImportError:
    from pathlib2 import Path

import pytest

from sendto_silhouette import SendtoSilhouette


@pytest.fixture
def data_dir():
    return Path(__file__).parent / 'data'


def test_loading_duplicated_path(data_dir):
    effect = SendtoSilhouette()
    effect.parse_arguments([str(data_dir / 'plus_with_duplicate.svg')])
    effect.load_raw()
    effect.recursivelyTraverseSvg(effect.document.getroot())

    assert effect.paths == [
        # First cross
        [(10.0, 0.0), (10.0, 20.0)],
        [(0.0, 10), (20.0, 10)],
        # Second cross, the duplicate
        [(30.0, 20.0), (30.0, 40.0)],
        [(20.0, 30), (40.0, 30)],
    ]
