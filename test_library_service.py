import unittest
from datetime import date, timedelta
from library_service import filter_loans_due_next_week, is_book_already_in_tasks, clean_title

class TestLibraryService(unittest.TestCase):
    def test_filter_loans_due_next_week(self):
        ref_date = date(2026, 10, 17)
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

    def test_clean_title(self):
        self.assertEqual(clean_title("Sonic Prime"), "sonic prime")
        self.assertEqual(clean_title("Return: Sonic Prime"), "sonic prime")
        self.assertEqual(clean_title("Return: Sonic Prime. Volume 1"), "sonic prime")
        self.assertEqual(clean_title("Sonic Prime: Shattered"), "sonic prime")
        self.assertEqual(clean_title("Return book: Sonic Prime [Season 1]"), "sonic prime")

    def test_sonic_prime_completed_duplicate(self):
        # Scenario where task in Google Tasks was completed
        existing_tasks = [
            {
                "id": "t1",
                "title": "Return: Sonic Prime",
                "status": "completed",
                "notes": "Library: Cupertino Library (SCCLD)\nDue Date: Sun, Oct 25, 2026",
                "hidden": True,
            }
        ]

        # Case A: Library returns 'Sonic Prime. Volume 1'
        book_a = {"title": "Sonic Prime. Volume 1", "checkout_id": "123456"}
        is_dup, reason = is_book_already_in_tasks(book_a, existing_tasks)
        self.assertTrue(is_dup, f"Expected duplicate but got False. Reason: {reason}")
        self.assertIn("completed", reason)

        # Case B: Checked in sync_state
        sync_state = {"synced_checkout_ids": {"123456": {"title": "Sonic Prime"}}, "synced_titles": ["sonic prime"]}
        is_dup_state, reason_state = is_book_already_in_tasks(book_a, [], sync_state=sync_state)
        self.assertTrue(is_dup_state)
        self.assertIn("sync history", reason_state)

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

        book_completed = {"title": "Clean Code", "checkout_id": "987654"}
        is_dup, reason = is_book_already_in_tasks(book_completed, existing_tasks)
        self.assertTrue(is_dup)
        self.assertIn("completed", reason)

        book_active = {"title": "Design Patterns", "checkout_id": "112233"}
        is_dup, reason = is_book_already_in_tasks(book_active, existing_tasks)
        self.assertTrue(is_dup)

        book_new = {"title": "Refactoring", "checkout_id": "556677"}
        is_dup, reason = is_book_already_in_tasks(book_new, existing_tasks)
        self.assertFalse(is_dup)

if __name__ == "__main__":
    unittest.main()
