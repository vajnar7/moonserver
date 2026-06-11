import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:5000"


def http_request(path, method="GET", data=None):
    url = BASE_URL + path
    headers = {"Content-Type": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_state(target_state, timeout=10.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            status = http_request("/state")
        except Exception as exc:
            print(f"Waiting for Flask app: {exc}")
            time.sleep(0.5)
            continue
        print("Current state:", status)
        if status.get("state") == target_state:
            return status
        time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for state {target_state}")


def run_demo():
    python = sys.executable

    emulator = subprocess.Popen([python, "io_emulator.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    app = subprocess.Popen([python, "app.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    try:
        print("Started emulator and Flask app.")
        time.sleep(2.0)

        print("Checking app readiness...")
        wait_for_state("ready", timeout=15.0)

        print("Sending connect command...")
        response = http_request("/command/connect", method="POST")
        print("Connect response:", response)

        state = wait_for_state("connected", timeout=15.0)
        print("Connected state reached:", state)

        print("Sending move command...")
        response = http_request("/command/move", method="POST", data={"distance": 100})
        print("Move response:", response)

        state = wait_for_state("connected", timeout=15.0)
        print("Move completed, returned to connected state:", state)

    except Exception as exc:
        print(f"Demo failed: {exc}")
    finally:
        print("Stopping processes...")
        app.terminate()
        emulator.terminate()
        try:
            app.wait(timeout=5)
        except subprocess.TimeoutExpired:
            app.kill()
        try:
            emulator.wait(timeout=5)
        except subprocess.TimeoutExpired:
            emulator.kill()
        print("Demo finished.")


if __name__ == "__main__":
    run_demo()
