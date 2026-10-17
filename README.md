# Jenny Home Dashboard

## Set Up
### Create Google Project
* Open [Google Cloud Console](https://console.cloud.google.com/?utm_source=chatgpt.com)
* Create a project if you don't have project or want to use a different one.
* Go to APIs & Services → Library
  * Enable Google Calendar API
  * Enable Google Tasks API
* Go to APIs & Services → Credentials
  * Create Credentials → OAuth client ID
  * Configure OAuth consent screen if not have done before.
  * Application type → Desktop app
  * Download json as credentials.json

### Generate token
* clone the repository to local `~/calendar-dashboard`
* install the library `pip install --no-cache-dir -r requirements.txt`
* `source venv/bin/activate`
* place the credentials.json file from previous step in the same directory `~/calendar-dashboard/credentials.json`
* run the auth app `python3 auth.app`
* If the machine doesn't have Desktop, like running on a headless vm, build a tunnel and do the oauth from the laptop:
`ssh -L 8080:localhost:8080 pi@<ip>`
* Access the url to login and grant permission
* token.json is generated, and it will be used by docker to access the data.

## Run

### Run the docker
* docker will mass up the network, because it uses some broadcast.

### Run as a service
```
sudo nano /etc/systemd/system/calendar-dashboard.service
[Unit]
Description=Calendar Dashboard
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/calendar-dashboard
ExecStart=/home/pi/calendar-dashboard/venv/bin/python /home/pi/calendar-dashboard/start.py
Restart=always
RestartSec=5
Environment="HOME=/home/pi"

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable calendar-dashboard
sudo systemctl start calendar-dashboard
sudo systemctl status calendar-dashboard
```

## Cupertino Library (SCCLD) Return Reminder

Automatically fetches books due next week from your Cupertino Library (Santa Clara County Library District) account every Saturday at 8:00 AM and syncs them to Google Tasks under a dedicated "Library" list.

### 1. Configure Library Credentials
Copy the example config:
```bash
cp library_config.example.json library_config.json
```
Edit `library_config.json`:
```json
{
  "card_number": "YOUR_LIBRARY_CARD_NUMBER",
  "pin": "YOUR_PIN",
  "subdomain": "sccl",
  "task_list_name": "Library",
  "sync_day_of_week": 5,
  "sync_hour": 8,
  "sync_minute": 0,
  "days_ahead": 8,
  "timezone": "America/Los_Angeles"
}
```
Or run the interactive setup wizard:
```bash
python3 library_service.py --setup
```

### 2. Manual Commands
* **Test connection & list current loans:**
  ```bash
  python3 library_service.py --list-loans
  ```
* **Run sync immediately:**
  ```bash
  python3 library_service.py --sync
  ```
* **Trigger via Web API:**
  ```bash
  curl -X POST http://localhost:8080/api/library/sync
  ```
