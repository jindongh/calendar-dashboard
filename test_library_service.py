import unittest
from datetime import date, timedelta
from library_service import filter_loans_due_next_week, is_book_already_in_tasks

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

    def test_is_book_already_in_tasks_completed(self):
        existing_tasks = [
            {
                "id": "1",
                "title": "Return: Clean Code",
                "status": "completed",
                "notes": "Due Date: 2026-10-20\nCheckout ID: 987654",
                "hidden": True,
            },
            {
                "id": "2",
                "title": "Return: Design Patterns",
                "status": "needsAction",
                "notes": "Checkout ID: 112233",
            },
        ]

        # Book 1: Already completed in todo -> should be detected as duplicate!
        book_completed = {"title": "Clean Code", "checkout_id": "987654"}
        is_dup, reason = is_book_already_in_tasks(book_completed, existing_tasks)
        self.assertTrue(is_dup)
        self.assertIn("completed", reason)

        # Book 2: Active in todo -> duplicate!
        book_active = {"title": "Design Patterns", "checkout_id": "112233"}
        is_dup, reason = is_book_already_in_tasks(book_active, existing_tasks)
        self.assertTrue(is_dup)

        # Book 3: Brand new book -> not duplicate!
        book_new = {"title": "Refactoring", "checkout_id": "556677"}
        is_dup, reason = is_book_already_in_tasks(book_new, existing_tasks)
        self.assertFalse(is_dup)

if __name__ == "__main__":
    unittest.main()
