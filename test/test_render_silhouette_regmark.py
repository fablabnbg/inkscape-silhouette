#!/usr/bin/env python3
# coding=utf-8

from render_silhouette_regmarks import InsertRegmark
from inkex import BoundingBox
from inkex.tester import TestCase


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
            self.e.svg.getElementById('regmark-tl').tostring(),
            b'<rect x="10.0" y="10.0" width="5" height="5" style="fill:black"/>'
        )

        """Ensure top-right regmark"""
        self.assertEqual(
            self.e.svg.getElementById('regmark-tr').bounding_box(),
            BoundingBox((390.0, 410.0),(10.0, 30.0))
        )

        """Ensure x distance"""
        transform = self.e.svg.getElementById('regmark-tr').composed_transform()
        self.assertEqual(
            self.e.svg.unit_to_viewport(
                    (self.e.svg.getElementById('regmark-tr').bounding_box(transform).x.maximum
                    - self.e.svg.getElementById('regmark-bl').bounding_box(transform).x.minimum),
                "mm"),
            400
        )

        """Ensure y distance"""
        transform = self.e.svg.getElementById('regmark-tr').composed_transform()
        self.assertEqual(
            self.e.svg.unit_to_viewport(
                    (self.e.svg.getElementById('regmark-bl').bounding_box(transform).y.maximum
                    - self.e.svg.getElementById('regmark-tr').bounding_box(transform).y.minimum),
                "mm"),
            300
        )