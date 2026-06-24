import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.services.company_service import CompanyService
from core.database import init_db

class TestCompanyService(unittest.TestCase):
    def setUp(self):
        self.service = CompanyService()
        
    def test_get_all_companies(self):
        companies = self.service.get_all()
        self.assertIsInstance(companies, list, "Service should return a list even if empty")
        # Ensure it's returning dicts or objects we expect
        if len(companies) > 0:
            self.assertIn('id', companies[0], "Company dictionary must have 'id'")
            self.assertIn('ticker', companies[0], "Company dictionary must have 'ticker'")
            
    def test_search_company(self):
        # A search for gibberish should be None
        res = self.service.get_by_ticker("GIBBERISH_XYZ_123")
        self.assertIsNone(res)

if __name__ == '__main__':
    unittest.main()
