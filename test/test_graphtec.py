import unittest

from silhouette.Graphtec import (
    PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA,
    PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA_PLUS,
    _hardware_by_product_id,
)


class RegistrationMarkSettingsTest(unittest.TestCase):
    def test_cameo5_alpha_profiles_have_no_horizontal_margin(self):
        for product_id in (
            PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA,
            PRODUCT_ID_SILHOUETTE_CAMEO5ALPHA_PLUS,
        ):
            self.assertEqual(
                _hardware_by_product_id(product_id)["margin_left_mm"], 0.0
            )


if __name__ == "__main__":
    unittest.main()
