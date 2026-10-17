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


print("Starting Library Sync Scheduler...")


library_process = subprocess.Popen(
    [
        sys.executable,
        "library_service.py",
        "--scheduler",
    ]
)


try:

    while True:

        flask_code = flask_process.poll()
        cast_code = cast_process.poll()
        library_code = library_process.poll()

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

        if library_code is not None:

            print(
                f"Library scheduler exited with code {library_code}"
            )

            print(
                "Restarting Library Scheduler..."
            )

            time.sleep(5)

            library_process = subprocess.Popen(
                [
                    sys.executable,
                    "library_service.py",
                    "--scheduler",
                ]
            )

        time.sleep(5)


except KeyboardInterrupt:

    print("Stopping...")

    flask_process.terminate()
    cast_process.terminate()
    library_process.terminate()
