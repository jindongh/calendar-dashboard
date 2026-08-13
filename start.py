import subprocess
import time
import sys


print("Starting Calendar Dashboard...")


# Start Flask
flask_process = subprocess.Popen(
    [
        sys.executable,
        "app.py",
    ]
)


# Give Flask a few seconds to start
time.sleep(5)


print("Starting Nest Hub Cast...")


cast_process = subprocess.Popen(
    [
        sys.executable,
        "cast_dashboard.py",
    ]
)


try:

    while True:

        flask_code = flask_process.poll()
        cast_code = cast_process.poll()

        if flask_code is not None:

            print(
                f"Flask exited with code {flask_code}"
            )

            flask_process = subprocess.Popen(
                [
                    sys.executable,
                    "app.py",
                ]
            )

        if cast_code is not None:

            print(
                f"Cast process exited with code {cast_code}"
            )

            print(
                "Restarting Cast..."
            )

            time.sleep(5)

            cast_process = subprocess.Popen(
                [
                    sys.executable,
                    "cast_dashboard.py",
                ]
            )

        time.sleep(5)


except KeyboardInterrupt:

    print("Stopping...")

    flask_process.terminate()
    cast_process.terminate()
