import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from core.services.special_service import SpecialService

class TestSpecialService(unittest.TestCase):
    def setUp(self):
        self.service = SpecialService()
        
    def test_calculate_metrics_basic(self):
        data = {
            'strategy_type': 'Merger Arbitrage (Cash)',
            'tickers_dict': {'target': 'MSFT'},
            'entry_price': 100,
            'specific_data': {
                'deal_value': 120,
                'close_probability': 90,
                'downside_price': 80
            }
        }
        live_prices = {'MSFT': 110}
        
        core = self.service.calculate_metrics(data, live_prices)
        
        self.assertIn('target_implied', core)
        self.assertEqual(core['target_implied'], 120.0)
        self.assertIn('irr_market', core)
        
        # Expected Value = (120 - 110) * 0.9 + (80 - 110) * 0.1 
        # = 10 * 0.9 + (-30) * 0.1 = 9 - 3 = 6
        # Expected EV Price: 110 + 6 = 116
        self.assertAlmostEqual(core['ev_price'], 116.0, places=2)
        
    def test_fetch_summary(self):
        stats = self.service.get_summary_stats()
        self.assertIn('total', stats)
        self.assertIn('active_count', stats)

if __name__ == '__main__':
    unittest.main()
