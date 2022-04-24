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
    svg_path = str(data_dir / 'plus_with_duplicate.svg')
    if hasattr(effect, 'parse_arguments'):  # Inkscape 1.x
        effect.parse_arguments([svg_path])
        effect.load_raw()
    else:  # Inkscape 0.9x
        effect.getoptions([svg_path])
        effect.parse(svg_path)

    effect.recursivelyTraverseSvg(effect.document.getroot())

    assert effect.paths == [
        # First cross
        [(10.0, 0.0), (10.0, 20.0)],
        [(0.0, 10), (20.0, 10)],
        # Second cross, the duplicate
        [(30.0, 20.0), (30.0, 40.0)],
        [(20.0, 30), (40.0, 30)],
    ]
