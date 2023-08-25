#!/usr/bin/env python3
# coding=utf-8

from render_silhouette_regmarks import InsertRegmark
from inkex import BoundingBox
from inkex.tester import TestCase

REGMARK_LAYERNAME = 'Regmarks'
REGMARK_LAYER_ID = 'regmark'
REGMARK_TOP_LEFT_ID = 'regmark-tl'
REGMARK_TOP_RIGHT_ID = 'regmark-tr'
REGMARK_BOTTOM_LEFT_ID = 'regmark-bl'
REGMARK_SAFE_AREA_ID = 'regmark-safe-area'
REGMARK_NOTES_ID = 'regmark-notes'

class InsertRegmarkTest(TestCase):
    """Tests for Inkscape Extensions"""

    effect_class = InsertRegmark

    def setUp(self):
        self.e = self.effect_class()


class RegmarkTest(InsertRegmarkTest):
    source_file = "plus_with_duplicate.svg"

    def test_regmarks(self):
        self.e.parse_arguments([self.data_file(self.source_file), "--reglength=300"])
        self.e.load_raw()
        self.e.effect()

        """Ensure top-left regmark"""
        self.assertEqual(
            self.e.svg.getElementById(REGMARK_TOP_LEFT_ID).tostring(),
            b'<rect x="10.0" y="10.0" width="5" height="5" style="fill:black"/>'
        )

        """Ensure top-right regmark"""
        self.assertEqual(
            self.e.svg.getElementById(REGMARK_TOP_RIGHT_ID).bounding_box(),
            BoundingBox((390.0, 410.0),(10.0, 30.0))
        )

        """Ensure x distance"""
        self.assertEqual(
            self.e.svg.unit_to_viewport(
                    (self.e.svg.getElementById(REGMARK_TOP_RIGHT_ID).bounding_box(transform=True).x.maximum
                    - self.e.svg.getElementById(REGMARK_BOTTOM_LEFT_ID).bounding_box(transform=True).x.minimum),
                "mm"),
            400
        )

        """Ensure y distance"""
        self.assertEqual(
            self.e.svg.unit_to_viewport(
                    (self.e.svg.getElementById(REGMARK_BOTTOM_LEFT_ID).bounding_box(transform=True).y.maximum
                    - self.e.svg.getElementById(REGMARK_TOP_RIGHT_ID).bounding_box(transform=True).y.minimum),
                "mm"),
            300
        )