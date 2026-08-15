import time
from datetime import datetime

import pychromecast
from pychromecast.controllers.dashcast import DashCastController
from pychromecast.config import APP_DASHCAST


# ============================================================
# Configuration
# ============================================================

NEST_HUB_NAME = "Living Room Display"

PI_IP = "192.168.86.111"
DASHBOARD_URL = f"http://{PI_IP}:8080"

CHECK_INTERVAL = 10
RETRY_INTERVAL = 30


# ============================================================
# Logging
# ============================================================

def log(message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {message}", flush=True)


# ============================================================
# Find our Nest Hub
# ============================================================

def find_nest_hub(chromecasts):

    for cast in chromecasts:

        host = getattr(
            cast.cast_info,
            "host",
            None
        )

        if cast.name == NEST_HUB_NAME:
            return cast

    return None


# ============================================================
# Cast Dashboard
# ============================================================

def cast_dashboard(cast):

    log("Starting Dashboard Cast...")

    try:

        cast.wait()

        dashcast = DashCastController()

        cast.register_handler(dashcast)

        dashcast.load_url(
            DASHBOARD_URL,
            force=True,
        )

        log(
            f"Dashboard sent to "
            f"{cast.name}"
        )

        log(
            f"URL: {DASHBOARD_URL}"
        )

        return True

    except Exception as e:

        log(
            f"Failed to cast Dashboard: "
            f"{type(e).__name__}: {e}"
        )

        return False


# ============================================================
# Check current Cast state
# ============================================================

def check_status(cast):

    try:

        cast.wait()

        status = cast.status

        app_id = status.app_id
        app_name = status.display_name

        return app_id, app_name

    except Exception as e:

        log(
            f"Could not read Nest Hub status: "
            f"{type(e).__name__}: {e}"
        )

        return None, None


# ============================================================
# Main watchdog
# ============================================================

def main():

    log("Nest Hub Watchdog starting")

    log(
        f"Target: {NEST_HUB_NAME} "
    )

    log(
        f"Dashboard: {DASHBOARD_URL}"
    )

    log(
        f"Expected Cast App ID: "
        f"{APP_DASHCAST}"
    )


    # --------------------------------------------------------
    # Start Cast discovery
    # --------------------------------------------------------

    log("Searching for Cast devices...")

    chromecasts, browser = (
        pychromecast.get_chromecasts()
    )

    try:

        cast = None
        last_state = None
        last_cast_time = 0


        while True:

            # =================================================
            # Find Nest Hub
            # =================================================

            if cast is None:

                cast = find_nest_hub(
                    chromecasts
                )

                if cast is None:

                    log(
                        "Nest Hub not found. "
                        f"Retrying in "
                        f"{RETRY_INTERVAL}s..."
                    )

                    time.sleep(
                        RETRY_INTERVAL
                    )

                    continue


                log(
                    f"Found Nest Hub: "
                    f"{cast.name} "
                    f"({cast.cast_info.host})"
                )


                # =============================================
                # Initial Cast
                # =============================================

                if cast_dashboard(cast):

                    last_cast_time = time.time()

                    last_state = None

                else:

                    cast = None

                    time.sleep(
                        RETRY_INTERVAL
                    )

                    continue


            # =================================================
            # Check current state
            # =================================================

            app_id, app_name = check_status(
                cast
            )


            # -------------------------------------------------
            # Nest Hub disconnected
            # -------------------------------------------------

            if app_id is None:

                log(
                    "Nest Hub status unavailable. "
                    "Will retry..."
                )

                cast = None

                time.sleep(
                    RETRY_INTERVAL
                )

                continue


            # =================================================
            # Log state changes only
            # =================================================

            current_state = (
                app_id,
                app_name
            )

            if current_state != last_state:

                log(
                    f"Nest Hub state: "
                    f"APP_ID={app_id}, "
                    f"APP={app_name}"
                )

                last_state = current_state


            # =================================================
            # Dashboard is running normally
            # =================================================

            if app_id == APP_DASHCAST:

                time.sleep(
                    CHECK_INTERVAL
                )

                continue


            # =================================================
            # Something else is running
            #
            # Example:
            #
            # APP_ID: E8C28D3C
            # APP: Backdrop
            #
            # =================================================

            log(
                "Dashboard is no longer active."
            )

            log(
                f"Current app: "
                f"{app_name} "
                f"({app_id})"
            )

            log(
                "Restoring Dashboard..."
            )


            # Prevent rapid repeated Cast attempts

            now = time.time()

            if (
                now - last_cast_time
                < 5
            ):

                time.sleep(
                    CHECK_INTERVAL
                )

                continue


            if cast_dashboard(cast):

                last_cast_time = time.time()

                log(
                    "Dashboard restored."
                )

            else:

                log(
                    "Dashboard restore failed. "
                    "Will retry."
                )


            time.sleep(
                CHECK_INTERVAL
            )


    finally:

        log(
            "Stopping Cast discovery..."
        )

        browser.stop_discovery()


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":

    main()
