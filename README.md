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
* `docker compose build --no-cache`
* `docker compose up -d`

### Run the docker in another machine.
If you want to run the docker in a new machine, just clone the repository and token.json, and then do the same thing:
* `docker compose build --no-cache`
* `docker compose up -d`
