from flask import Flask, jsonify, render_template
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import json
from urllib.request import urlopen
from urllib.parse import urlencode

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks",
]

TIMEZONE = ZoneInfo("America/Los_Angeles")
WEATHER_LATITUDE = 37.3688
WEATHER_LONGITUDE = -122.0363


WEATHER_CODES = {
    0: ("☀️", "Clear"),
    1: ("🌤️", "Mainly clear"),
    2: ("⛅", "Partly cloudy"),
    3: ("☁️", "Cloudy"),
    45: ("🌫️", "Fog"),
    48: ("🌫️", "Fog"),
    51: ("🌦️", "Light drizzle"),
    53: ("🌦️", "Drizzle"),
    55: ("🌧️", "Heavy drizzle"),
    61: ("🌦️", "Light rain"),
    63: ("🌧️", "Rain"),
    65: ("🌧️", "Heavy rain"),
    71: ("🌨️", "Light snow"),
    73: ("🌨️", "Snow"),
    75: ("❄️", "Heavy snow"),
    80: ("🌦️", "Rain showers"),
    81: ("🌧️", "Rain showers"),
    82: ("⛈️", "Heavy showers"),
    95: ("⛈️", "Thunderstorm"),
    96: ("⛈️", "Thunderstorm"),
    99: ("⛈️", "Thunderstorm"),
}


def get_weather():
    params = urlencode({
        "latitude": WEATHER_LATITUDE,
        "longitude": WEATHER_LONGITUDE,
        "current": "temperature_2m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min",
        "temperature_unit": "fahrenheit",
        "timezone": "America/Los_Angeles",
        "forecast_days": 1,
    })

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + params
    )

    with urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))

    current = data["current"]
    daily = data["daily"]

    code = current["weather_code"]

    icon, description = WEATHER_CODES.get(
        code,
        ("🌡️", "Unknown")
    )

    return {
        "temperature": round(
            current["temperature_2m"]
        ),
        "high": round(
            daily["temperature_2m_max"][0]
        ),
        "low": round(
            daily["temperature_2m_min"][0]
        ),
        "icon": icon,
        "description": description,
    }


def load_credentials():
    creds = Credentials.from_authorized_user_file(
        str(BASE_DIR / "token.json"),
        SCOPES,
    )

    # Refresh automatically if the access token expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

        with open(BASE_DIR / "token.json", "w") as token:
            token.write(creds.to_json())

    return creds


creds = load_credentials()

calendar_service = build(
    "calendar",
    "v3",
    credentials=creds,
)

tasks_service = build(
    "tasks",
    "v1",
    credentials=creds,
)


def parse_google_datetime(value):
    """Convert Google datetime to local timezone."""
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).astimezone(TIMEZONE)
    except Exception:
        return None


def get_calendar_events():
    now = datetime.now(TIMEZONE)

    start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    end = start + timedelta(days=7)

    # Get all calendars visible to this account
    calendar_list = calendar_service.calendarList().list(
        maxResults=100
    ).execute()

    events = []

    for calendar in calendar_list.get("items", []):

        calendar_id = calendar["id"]

        calendar_name = calendar.get(
            "summary",
            calendar_id
        )

        # Skip calendars that are hidden
        if calendar.get("selected") is False:
            continue

        try:

            result = calendar_service.events().list(
                calendarId=calendar_id,
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                maxResults=100,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

        except Exception as e:

            print(
                f"Cannot read calendar "
                f"{calendar_name}: {e}"
            )

            continue

        for event in result.get("items", []):

            start_info = event.get(
                "start",
                {}
            )

            # =========================
            # Timed event
            # =========================

            if "dateTime" in start_info:

                dt = parse_google_datetime(
                    start_info["dateTime"]
                )

                if not dt:
                    continue

                events.append({

                    "id": event.get("id"),

                    "calendar_id":
                        calendar_id,

                    "calendar_name":
                        calendar_name,

                    "title":
                        event.get(
                            "summary",
                            "(No title)"
                        ),

                    "date":
                        dt.strftime(
                            "%Y-%m-%d"
                        ),

                    "date_display":
                        dt.strftime(
                            "%a, %b %-d"
                        ),

                    "time":
                        dt.strftime(
                            "%-I:%M %p"
                        ),

                    "all_day":
                        False,

                    "timestamp":
                        dt.timestamp(),

                })

            # =========================
            # All-day event
            # =========================

            elif "date" in start_info:

                date_string = start_info["date"]

                try:
                    local_date = datetime.strptime(
                            date_string,
                            "%Y-%m-%d"
                        )
                except ValueError:
                    continue

                events.append({

                    "id":
                        event.get("id"),

                    "calendar_id":
                        calendar_id,

                    "calendar_name":
                        calendar_name,

                    "title":
                        event.get(
                            "summary",
                            "(No title)"
                        ),

                    "date":
                        date_string,

                    "date_display":
                        local_date.strftime(
                            "%a, %b %-d"
                        ),

                    "time":
                        "All day",

                    "all_day":
                        True,

                    "timestamp":
                        local_date.replace(
                            tzinfo=TIMEZONE
                        ).timestamp(),

                })


    # Sort all calendars together
    events.sort(
        key=lambda e: e["timestamp"]
    )

    return events


def get_tasks():
    task_lists_result = tasks_service.tasklists().list(
        maxResults=100
    ).execute()

    tasks = []

    for task_list in task_lists_result.get("items", []):

        task_list_id = task_list["id"]
        task_list_name = task_list.get(
            "title",
            "Tasks"
        )

        result = tasks_service.tasks().list(
            tasklist=task_list_id,
            showCompleted=False,
            showHidden=False,
            maxResults=100,
        ).execute()

        for task in result.get("items", []):

            # Google Tasks may return due as UTC
            due_value = task.get("due")

            due_date = None
            due_display = None

            if not due_value:
                continue
            due_dt = datetime.strptime(
                due_value[:10],
                "%Y-%m-%d"
            ).date()

            if due_dt:
                due_date = due_dt.strftime(
                    "%Y-%m-%d"
                )
                due_display = due_dt.strftime(
                    "%a, %b %-d"
                )

            tasks.append({
                "id": task["id"],
                "list_id": task_list_id,
                "list": task_list_name,
                "title": task.get(
                    "title",
                    "(No title)"
                ),
                "due": due_date,
                "due_display": due_display,
            })

    # Sort:
    # 1. tasks with due dates
    # 2. overdue/today first
    # 3. undated tasks last
    tasks.sort(
        key=lambda x: (
            x["due"] is None,
            x["due"] or "9999-12-31",
            x["title"].lower(),
        )
    )

    return tasks


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def data():

    try:
        events = get_calendar_events()
        tasks = get_tasks()

        return jsonify({
            "events": events,
            "tasks": tasks,
            "updated": datetime.now(
                TIMEZONE
            ).strftime(
                "%Y-%m-%d %I:%M:%S %p"
            ),
        })

    except Exception as e:

        print("ERROR:", repr(e))

        return jsonify({
            "error": str(e),
        }), 500


@app.route("/api/weather")
def weather():
    try:
        return jsonify(get_weather())
    except Exception as e:
        print(
            "WEATHER ERROR:",
            repr(e)
        )

        return jsonify({
            "error": str(e)
        }), 500


@app.route(
    "/api/tasks/<list_id>/<task_id>/complete",
    methods=["POST"]
)
def complete_task(list_id, task_id):

    try:

        # Get current task
        task = tasks_service.tasks().get(
            tasklist=list_id,
            task=task_id,
        ).execute()

        # Mark it completed
        task["status"] = "completed"

        updated_task = tasks_service.tasks().update(
            tasklist=list_id,
            task=task_id,
            body=task,
        ).execute()

        return jsonify({
            "success": True,
            "id": updated_task["id"],
            "status": updated_task["status"],
        })

    except Exception as e:

        print(
            "TASK COMPLETE ERROR:",
            repr(e)
        )

        return jsonify({
            "success": False,
            "error": str(e),
        }), 500


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
    )
