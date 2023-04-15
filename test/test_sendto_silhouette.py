from pathlib import Path

import pytest

from sendto_silhouette import SendtoSilhouette
from inkex import Transform


@pytest.fixture
def data_dir():
    return Path(__file__).parent / 'data'


def test_loading_duplicated_path(data_dir):
    effect = SendtoSilhouette()
    svg_path = str(data_dir / 'plus_with_duplicate.svg')
    effect.parse_arguments([svg_path])
    effect.load_raw()
    effect.clean_up()

    effect.recursivelyTraverseSvg(effect.document.getroot())

    assert effect.paths == [
        # First cross
        [(10.0, 0.0), (10.0, 20.0)],
        [(0.0, 10.0), (20.0, 10.0)],
        # Second cross, the duplicate
        [(30.0, 20.0), (30.0, 40.0)],
        [(20.0, 30.0), (40.0, 30.0)],
    ]

def test_loading_duplicated_path_docscale(data_dir):
    effect = SendtoSilhouette()
    svg_path = str(data_dir / 'plus_with_duplicate.svg')
    effect.parse_arguments([svg_path])
    effect.load_raw()

    # mocking `effect.handleViewBox()`
    effect.docTransform = Transform(scale=(2))

    effect.clean_up()

    effect.recursivelyTraverseSvg(effect.document.getroot())

    assert effect.paths == [
        # First cross
        [(20.0, 0.0), (20.0, 40.0)],
        [(0.0, 20.0), (40.0, 20.0)],
        # Second cross, the duplicate
        [(60.0, 40.0), (60.0, 80.0)],
        [(40.0, 60.0), (80.0, 60.0)],
    ]

def test_loading_composed_transform_use(data_dir):
    effect = SendtoSilhouette()
    svg_path = str(data_dir / 'composed_transform.test.svg')
    effect.parse_arguments([svg_path])
    effect.load_raw()

    # mocking `effect.handleViewBox()`
    effect.docTransform = Transform(scale=(2))

    effect.clean_up()

    effect.recursivelyTraverseSvg(effect.document.getroot())

    assert effect.paths == [
        # First rect
        [(20.0, 0.0), (40.0, 0.0), (40.0, 20.0), (20.0, 20.0), (20.0, 0.0)],
        # Second rect, the clone
        [(0.0, 20.0), (20.0, 20.0), (20.0, 40.0), (0.0, 40.0), (0.0, 20.0)],
    ]
