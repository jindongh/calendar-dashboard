#!/usr/bin/env python3
"""
Cupertino Library (SCCLD) to Google Tasks Sync Service.

Fetches checked-out books from Santa Clara County Library District (BiblioCommons)
and creates return reminders in Google Tasks under the "Library" list.
"""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "library_config.json"
TOKEN_PATH = BASE_DIR / "token.json"
DEFAULT_TIMEZONE = ZoneInfo("America/Los_Angeles")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks",
]

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("library_service")


class CupertinoLibraryClient:
    """Client for logging into SCCLD (BiblioCommons) and retrieving checked out books."""

    def __init__(self, subdomain: str = "sccl"):
        self.subdomain = subdomain
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        self.account_id = None
        self.bc_access_token = None
        self.session_id = None

    def login(self, card_number: str, pin: str) -> bool:
        """Authenticate with BiblioCommons using library card number and PIN."""
        login_url = f"https://{self.subdomain}.bibliocommons.com/user/login"
        logger.info(f"Connecting to library login page ({self.subdomain}.bibliocommons.com)...")

        resp = self.session.get(login_url, timeout=20)
        resp.raise_for_status()

        post_url = resp.url

        # Extract Rails CSRF authenticity token
        m = re.search(r'name=[\"\']authenticity_token[\"\'][^>]*value=[\"\']([^\"\']+)[\"\']', resp.text)
        if not m:
            m = re.search(r'value=[\"\']([^\"\']+)[\"\'][^>]*name=[\"\']authenticity_token[\"\']', resp.text)

        if not m:
            raise RuntimeError("Could not find authenticity_token on library login page.")

        token = m.group(1)

        post_data = {
            "utf8": "✓",
            "authenticity_token": token,
            "name": str(card_number).strip(),
            "user_pin": str(pin).strip(),
            "local": "false",
            "remember_me": "true",
            "commit": "Log In",
        }

        post_headers = {
            "Referer": post_url,
            "Origin": f"https://{self.subdomain}.bibliocommons.com",
        }

        logger.info("Submitting library credentials...")
        # Note: Do not raise_for_status() on post_resp because redirects after successful
        # login might hit landing URLs that return 404, but the required session cookies
        # (bc_access_token & session_id) are already captured in session.cookies.
        self.session.post(
            post_url,
            data=post_data,
            headers=post_headers,
            allow_redirects=True,
            timeout=25,
        )

        # Extract authentication cookies
        cookies = self.session.cookies.get_dict()
        self.bc_access_token = cookies.get("bc_access_token")
        self.session_id = cookies.get("session_id")

        if not self.bc_access_token or not self.session_id:
            # Check flash cookie or page text for error indication
            err_msg = "Invalid card number or PIN"
            for cookie_val in cookies.values():
                if "incorrect" in cookie_val.lower() or "invalid" in cookie_val.lower():
                    err_msg = "Library rejected credentials: " + cookie_val
                    break
            raise RuntimeError(f"Library authentication failed. {err_msg}")

        # Account ID is derived from session_id
        # Example session_id: '...-1234567' -> account_id = 1234568
        self.account_id = int(self.session_id.split("-")[-1]) + 1
        logger.info(f"Successfully authenticated with library (account_id: {self.account_id}).")
        return True

    def get_checkouts(self) -> dict:
        """Fetch raw checkouts JSON from BiblioCommons Gateway API."""
        if not self.account_id or not self.bc_access_token:
            raise RuntimeError("Not authenticated. Call login() first.")

        gateway_url = f"https://gateway.bibliocommons.com/v2/libraries/{self.subdomain}/checkouts"
        params = {
            "accountId": self.account_id,
            "size": 100,
        }
        headers = {
            "X-Access-Token": self.bc_access_token,
            "X-Session-Id": self.session_id,
            "Origin": f"https://{self.subdomain}.bibliocommons.com",
            "Referer": f"https://{self.subdomain}.bibliocommons.com/",
            "Accept": "application/json",
        }

        logger.info(f"Fetching checked out items from {gateway_url}...")
        resp = self.session.get(gateway_url, params=params, headers=headers, timeout=25)
        resp.raise_for_status()
        return resp.json()

    def get_loans(self) -> list[dict]:
        """Parse loans into structured book objects."""
        data = self.get_checkouts()
        checkouts = data.get("entities", {}).get("checkouts", {})
        bibs = data.get("entities", {}).get("bibs", {})

        loans = []
        for checkout_id, item in checkouts.items():
            metadata_id = item.get("metadataId")
            bib = bibs.get(metadata_id, {})
            brief = bib.get("briefInfo", {}) if bib else {}

            title = brief.get("title") or item.get("bibTitle") or "(Untitled)"
            subtitle = brief.get("subtitle") or ""
            authors_list = brief.get("authors") or []
            author = ", ".join(authors_list) if isinstance(authors_list, list) else str(authors_list)

            due_date_str = item.get("dueDate")
            due_date = None
            if due_date_str:
                try:
                    due_date = date.fromisoformat(due_date_str[:10])
                except Exception:
                    pass

            format_type = brief.get("format") or item.get("format") or "Book"
            actions = item.get("actions") or []

            loans.append({
                "checkout_id": str(checkout_id),
                "metadata_id": str(metadata_id or ""),
                "title": title.strip(),
                "subtitle": subtitle.strip(),
                "author": author.strip(),
                "due_date": due_date,
                "due_date_str": due_date.isoformat() if due_date else due_date_str,
                "format": format_type,
                "renewable": "renew" in actions,
            })

        loans.sort(key=lambda x: x["due_date"] or date.max)
        logger.info(f"Found {len(loans)} total checked out items.")
        return loans


def load_library_config() -> dict:
    """Load library_config.json if it exists."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config file not found at {CONFIG_PATH}. "
            "Please create it or copy library_config.example.json to library_config.json."
        )
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_google_tasks_service():
    """Load Google Tasks API service using existing token.json."""
    if not TOKEN_PATH.exists():
        raise FileNotFoundError(
            f"Google token file not found at {TOKEN_PATH}. "
            "Please run auth.py first to authorize Google Tasks."
        )

    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return build("tasks", "v1", credentials=creds)


def get_or_create_tasklist(tasks_service, list_name: str = "Library") -> str:
    """Find task list by name or create a new one."""
    res = tasks_service.tasklists().list(maxResults=100).execute()
    items = res.get("items", [])

    for item in items:
        if item.get("title", "").strip().lower() == list_name.strip().lower():
            return item["id"]

    # Not found, create it
    logger.info(f"Tasklist '{list_name}' not found. Creating it...")
    new_list = tasks_service.tasklists().insert(body={"title": list_name}).execute()
    return new_list["id"]


def filter_loans_due_next_week(loans: list[dict], ref_date: date = None, days_ahead: int = 8) -> list[dict]:
    """
    Filter loans that are due next week (or already overdue).
    If run on Saturday, days_ahead=8 includes all books due through the following Sunday.
    """
    if ref_date is None:
        ref_date = datetime.now(DEFAULT_TIMEZONE).date()

    cutoff_date = ref_date + timedelta(days=days_ahead)
    due_loans = []

    for loan in loans:
        due = loan.get("due_date")
        if due is None:
            continue
        # Include anything due on or before next week's Sunday
        if due <= cutoff_date:
            due_loans.append(loan)

    return due_loans


def load_all_existing_tasks(tasks_service, target_tasklist_id: str) -> list[dict]:
    """
    Fetch all tasks (including completed and hidden) with pagination
    from target task list and other visible task lists to avoid adding duplicate tasks.
    """
    all_tasks = []
    tasklist_ids = [target_tasklist_id]

    try:
        tasklists_res = tasks_service.tasklists().list(maxResults=100).execute()
        for tl in tasklists_res.get("items", []):
            if tl["id"] not in tasklist_ids:
                tasklist_ids.append(tl["id"])
    except Exception as e:
        logger.warning(f"Could not list all tasklists: {e}. Scanning target list only.")

    for t_id in tasklist_ids:
        page_token = None
        while True:
            try:
                res = tasks_service.tasks().list(
                    tasklist=t_id,
                    showCompleted=True,
                    showHidden=True,
                    maxResults=100,
                    pageToken=page_token,
                ).execute()
                all_tasks.extend(res.get("items", []))
                page_token = res.get("nextPageToken")
                if not page_token:
                    break
            except Exception as e:
                logger.error(f"Error fetching tasks from tasklist {t_id}: {e}")
                break

    return all_tasks


def is_book_already_in_tasks(book: dict, existing_tasks: list[dict]) -> tuple[bool, str]:
    """
    Check if a book is already present in tasks (active, completed, or hidden).
    Returns (is_duplicate, reason).
    """
    book_title = book.get("title", "").strip().lower()
    checkout_id = str(book.get("checkout_id", "")).strip()
    checkout_id_marker = f"checkout id: {checkout_id}".lower() if checkout_id else None

    expected_titles = {
        f"return: {book_title}",
        f"return book: {book_title}",
        book_title,
    }

    for task in existing_tasks:
        task_title = task.get("title", "").strip().lower()
        task_notes = task.get("notes", "").lower()
        task_status = task.get("status", "needsAction")
        is_completed = (task_status == "completed" or task.get("hidden") is True)
        status_suffix = " [completed]" if is_completed else ""

        # 1. Match by Checkout ID in notes (exact identifier from library)
        if checkout_id_marker and checkout_id_marker in task_notes:
            return True, f"Matched Checkout ID {checkout_id}{status_suffix}"

        # 2. Match by exact title variants
        if task_title in expected_titles:
            return True, f"Matched task title '{task.get('title')}'{status_suffix}"

        # 3. Match if task title starts with 'return' and contains the full book title
        if (task_title.startswith("return:") or task_title.startswith("return book:")) and book_title in task_title:
            return True, f"Matched return title pattern '{task.get('title')}'{status_suffix}"

    return False, ""


def sync_library_tasks(config: dict = None) -> dict:
    """
    Main synchronization routine:
    1. Log into Cupertino Library.
    2. Retrieve loans.
    3. Filter books due next week (or overdue).
    4. Sync with Google Tasks in the 'Library' list (preventing duplicates, even if completed).
    """
    if config is None:
        config = load_library_config()

    card_number = config.get("card_number")
    pin = config.get("pin")
    subdomain = config.get("subdomain", "sccl")
    task_list_name = config.get("task_list_name", "Library")
    days_ahead = int(config.get("days_ahead", 8))

    if not card_number or not pin:
        raise ValueError("Missing 'card_number' or 'pin' in library_config.json")

    # Step 1: Connect to Library
    client = CupertinoLibraryClient(subdomain=subdomain)
    client.login(card_number=card_number, pin=pin)
    all_loans = client.get_loans()

    # Step 2: Filter books due next week
    now_date = datetime.now(DEFAULT_TIMEZONE).date()
    due_loans = filter_loans_due_next_week(all_loans, ref_date=now_date, days_ahead=days_ahead)
    logger.info(
        f"Filtered {len(due_loans)} books due on or before "
        f"{(now_date + timedelta(days=days_ahead)).isoformat()} (next week)."
    )

    # Step 3: Connect to Google Tasks
    tasks_service = load_google_tasks_service()
    task_list_id = get_or_create_tasklist(tasks_service, task_list_name)

    # Fetch ALL existing tasks (including completed and hidden) to avoid duplicates
    existing_tasks = load_all_existing_tasks(tasks_service, task_list_id)
    logger.info(
        f"Retrieved {len(existing_tasks)} existing tasks across task lists "
        "(including completed and hidden) for duplicate verification."
    )

    added_tasks = []
    skipped_tasks = []

    for book in due_loans:
        expected_title = f"Return: {book['title']}"

        is_dup, reason = is_book_already_in_tasks(book, existing_tasks)
        if is_dup:
            logger.info(f"Skipping already existing book in todo: '{book['title']}' ({reason})")
            skipped_tasks.append({
                "title": book["title"],
                "reason": reason,
            })
            continue

        # Format due date as RFC 3339 string at midnight UTC
        due_iso = f"{book['due_date'].strftime('%Y-%m-%d')}T00:00:00.000Z"
        checkout_id_marker = f"Checkout ID: {book['checkout_id']}"
        notes_lines = [
            f"Library: Cupertino Library (SCCLD)",
            f"Due Date: {book['due_date'].strftime('%a, %b %-d, %Y')}",
        ]
        if book.get("author"):
            notes_lines.append(f"Author: {book['author']}")
        if book.get("format"):
            notes_lines.append(f"Format: {book['format']}")
        notes_lines.append(checkout_id_marker)

        task_body = {
            "title": expected_title,
            "due": due_iso,
            "notes": "\n".join(notes_lines),
        }

        logger.info(f"Adding task: '{expected_title}' (Due: {book['due_date']})")
        created = tasks_service.tasks().insert(tasklist=task_list_id, body=task_body).execute()
        
        # Add newly created task to existing_tasks in-memory to prevent duplicates in same run
        existing_tasks.append({
            "id": created.get("id"),
            "title": expected_title,
            "notes": "\n".join(notes_lines),
            "status": "needsAction",
        })

        added_tasks.append({
            "task_id": created.get("id"),
            "title": expected_title,
            "due_date": book["due_date"].isoformat(),
        })

    logger.info(
        f"Library sync complete! Added: {len(added_tasks)}, "
        f"Skipped (already in todo/completed): {len(skipped_tasks)}, "
        f"Total loans: {len(all_loans)}."
    )

    return {
        "status": "success",
        "synced_at": datetime.now(DEFAULT_TIMEZONE).isoformat(),
        "total_loans": len(all_loans),
        "due_next_week_count": len(due_loans),
        "added_count": len(added_tasks),
        "skipped_count": len(skipped_tasks),
        "added_tasks": added_tasks,
        "due_loans": [
            {
                "title": b["title"],
                "author": b["author"],
                "due_date": b["due_date"].isoformat() if b.get("due_date") else None,
                "format": b["format"],
            }
            for b in due_loans
        ],
    }


def run_scheduler():
    """
    Scheduler loop: runs continuously and checks if it's Saturday 8:00 AM.
    """
    logger.info("Starting Library Sync Scheduler...")
    last_sync_date = None

    while True:
        try:
            config = load_library_config()
            target_weekday = int(config.get("sync_day_of_week", 5))  # 5 = Saturday
            target_hour = int(config.get("sync_hour", 8))
            target_minute = int(config.get("sync_minute", 0))

            now = datetime.now(DEFAULT_TIMEZONE)
            today_str = now.strftime("%Y-%m-%d")

            # Check if condition is met and hasn't run today
            if (
                now.weekday() == target_weekday
                and now.hour == target_hour
                and now.minute == target_minute
                and last_sync_date != today_str
            ):
                logger.info(f"Scheduled trigger activated at {now.isoformat()} (Saturday 8:00 AM)!")
                try:
                    result = sync_library_tasks(config)
                    last_sync_date = today_str
                    logger.info(f"Scheduled sync succeeded: {result}")
                except Exception as e:
                    logger.error(f"Error during scheduled sync: {e}", exc_info=True)

                # Sleep a bit to prevent re-triggering within the same minute
                time.sleep(60)

        except FileNotFoundError:
            logger.info("library_config.json not found yet. Scheduler waiting for configuration...")
            time.sleep(60)
            continue
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")

        time.sleep(30)


def interactive_setup():
    """CLI wizard to set up library credentials."""
    print("=== Cupertino Library (SCCLD) Configuration Setup ===")
    card = input("Enter Library Card Number: ").strip()
    pin = input("Enter Library PIN: ").strip()

    config = {
        "card_number": card,
        "pin": pin,
        "subdomain": "sccl",
        "task_list_name": "Library",
        "sync_day_of_week": 5,
        "sync_hour": 8,
        "sync_minute": 0,
        "days_ahead": 8,
        "timezone": "America/Los_Angeles",
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print(f"Configuration successfully saved to {CONFIG_PATH}!")


def main():
    parser = argparse.ArgumentParser(description="Cupertino Library Sync to Google Tasks")
    parser.add_argument("--sync", action="store_true", help="Run sync immediately once")
    parser.add_argument("--scheduler", action="store_true", help="Start background scheduler loop")
    parser.add_argument("--list-loans", action="store_true", help="List all currently borrowed books")
    parser.add_argument("--setup", action="store_true", help="Interactive credential setup wizard")

    args = parser.parse_args()

    if args.setup:
        interactive_setup()
        return

    if args.list_loans:
        config = load_library_config()
        client = CupertinoLibraryClient(subdomain=config.get("subdomain", "sccl"))
        client.login(config["card_number"], config["pin"])
        loans = client.get_loans()
        print(f"\n===== CURRENT LOANS ({len(loans)}) =====")
        for l in loans:
            print(f"- {l['title']} by {l['author']} (Due: {l['due_date_str']}) [{l['format']}]")
        return

    if args.scheduler:
        run_scheduler()
        return

    # Default or --sync
    logger.info("Executing one-time library sync...")
    res = sync_library_tasks()
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
