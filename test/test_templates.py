import unittest
from pathlib import Path
from xml.etree import ElementTree

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
INKSCAPE_NAMESPACE = "http://www.inkscape.org/namespaces/inkscape"
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[1]
    / "templates"
    / "silhouette-cameo-5-alpha-registration-marks-a4.svg"
)


class Cameo5AlphaA4TemplateTest(unittest.TestCase):
    def test_page_and_regmark_geometry(self):
        root = ElementTree.parse(TEMPLATE_PATH).getroot()
        elements_by_id = {element.get("id"): element for element in root.iter()}
        expected_paths = {
            "regmark-tl": "M 30,10 H 10 V 30",
            "regmark-tr": "M 180,10 H 200 V 30",
            "regmark-bl": "M 30,287 H 10 V 267",
            "regmark-br": "M 180,287 H 200 V 267",
        }

        self.assertEqual(
            (root.get("width"), root.get("height"), root.get("viewBox")),
            ("210mm", "297mm", "0 0 210 297"),
        )
        for mark_id, path in expected_paths.items():
            mark = elements_by_id[mark_id]
            self.assertEqual(mark.tag, f"{{{SVG_NAMESPACE}}}path")
            self.assertEqual(mark.get("d"), path)

        layer = elements_by_id["regmark"]
        self.assertEqual(
            layer.get(f"{{{INKSCAPE_NAMESPACE}}}label"),
            "Regmarks",
        )
        self.assertEqual(layer.get("stroke"), "#000000")
        self.assertEqual(layer.get("stroke-width"), "0.3")
        self.assertEqual(layer.get("stroke-linecap"), "square")


if __name__ == "__main__":
    unittest.main()
