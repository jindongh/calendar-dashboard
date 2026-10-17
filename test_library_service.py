import unittest
from datetime import date, timedelta
from library_service import filter_loans_due_next_week

class TestLibraryService(unittest.TestCase):
    def test_filter_loans_due_next_week(self):
        # Suppose ref_date is Saturday, Oct 17
        ref_date = date(2026, 10, 17)
        # Next Sunday is Oct 25 (+8 days)

        loans = [
            {"title": "Book Overdue", "due_date": date(2026, 10, 10)},
            {"title": "Book Today", "due_date": date(2026, 10, 17)},
            {"title": "Book Mid Next Week", "due_date": date(2026, 10, 21)},
            {"title": "Book Next Sunday", "due_date": date(2026, 10, 25)},
            {"title": "Book Beyond Next Week", "due_date": date(2026, 10, 28)},
        ]

        filtered = filter_loans_due_next_week(loans, ref_date=ref_date, days_ahead=8)
        titles = [b["title"] for b in filtered]

        self.assertIn("Book Overdue", titles)
        self.assertIn("Book Today", titles)
        self.assertIn("Book Mid Next Week", titles)
        self.assertIn("Book Next Sunday", titles)
        self.assertNotIn("Book Beyond Next Week", titles)
        self.assertEqual(len(filtered), 4)

if __name__ == "__main__":
    unittest.main()
