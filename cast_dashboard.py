import time
import pychromecast

from pychromecast.controllers.dashcast import DashCastController


PI_IP = "192.168.86.111"
NEST_HUB_NAME = "Living Room Display"

DASHBOARD_URL = f"http://{PI_IP}:8080"


print("Searching for Cast devices...")

chromecasts, browser = pychromecast.get_chromecasts()

try:

    cast = None

    for device in chromecasts:

        print(
            f"Found: {device.name} "
            f"({device.model_name}) "
            f"{device.cast_info.host}"
        )

        if device.name == NEST_HUB_NAME:
            cast = device


    if cast is None:

        print(
            f"\nCould not find "
            f"'{NEST_HUB_NAME}'"
        )

        raise SystemExit(1)


    print()
    print("Using:", cast.name)

    cast.wait()


    # Create DashCast controller
    dashcast = DashCastController()

    cast.register_handler(dashcast)


    print("Loading Dashboard with DashCast...")

    # Let DashCast launch itself and load the URL.
    dashcast.load_url(
        DASHBOARD_URL,
        force=True,
    )


    print()
    print("Dashboard sent to:")
    print(cast.name)

    print("URL:", DASHBOARD_URL)


    # Keep the Cast connection alive.
    while True:

        time.sleep(60)


finally:

    browser.stop_discovery()
