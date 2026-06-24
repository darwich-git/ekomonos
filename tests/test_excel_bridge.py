import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.excel_bridge import map_month_id_to_es_str, normalize_str, safe_float

class TestExcelBridge(unittest.TestCase):
    def test_map_month_id_to_es_str(self):
        self.assertEqual(map_month_id_to_es_str("2026-01"), "Enero/26")
        self.assertEqual(map_month_id_to_es_str("2026-12"), "Diciembre/26")
        self.assertEqual(map_month_id_to_es_str("2025-05"), "Mayo/25")

    def test_normalize_str(self):
        self.assertEqual(normalize_str("Rafa"), "rafa")
        self.assertEqual(normalize_str("Enero/26"), "enero/26")
        # Unicode handling (accents)
        self.assertEqual(normalize_str("Campaña"), "campana")

    def test_safe_float(self):
        self.assertEqual(safe_float(None), 0.0)
        self.assertEqual(safe_float(10.5), 10.5)
        self.assertEqual(safe_float("150"), 150.0)
        self.assertEqual(safe_float("abc"), 0.0)

if __name__ == '__main__':
    unittest.main()
