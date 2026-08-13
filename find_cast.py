import pychromecast

print("Searching for Cast devices...")

chromecasts, browser = pychromecast.get_chromecasts()

try:
    for cast in chromecasts:
        print()
        print("Name:", cast.name)
        print("Model:", cast.model_name)
        print("Host:", cast.cast_info.host)
        print("Port:", cast.cast_info.port)

finally:
    browser.stop_discovery()
