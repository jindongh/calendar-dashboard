from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timezone

creds = Credentials.from_authorized_user_file(
    "token.json",
    [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/tasks",
    ],
)

# =========================
# Calendar
# =========================

calendar_service = build(
    "calendar",
    "v3",
    credentials=creds,
)

now = datetime.now(timezone.utc).isoformat()

events_result = calendar_service.events().list(
    calendarId="primary",
    timeMin=now,
    maxResults=10,
    singleEvents=True,
    orderBy="startTime",
).execute()

events = events_result.get("items", [])

print("\n===== CALENDAR =====")

for event in events:
    start = event["start"].get(
        "dateTime",
        event["start"].get("date")
    )

    print(start, "-", event.get("summary", "(No title)"))


# =========================
# Tasks
# =========================

tasks_service = build(
    "tasks",
    "v1",
    credentials=creds,
)

task_lists = tasks_service.tasklists().list().execute()

print("\n===== TASK LISTS =====")

for task_list in task_lists.get("items", []):
    print(
        task_list["id"],
        "-",
        task_list["title"]
    )

    tasks = tasks_service.tasks().list(
        tasklist=task_list["id"],
        showCompleted=False,
        showHidden=False,
    ).execute()

    for task in tasks.get("items", []):
        print(
            "  ☐",
            task.get("title", "(No title)")
        )
