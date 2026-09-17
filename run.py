import subprocess
import socket
import sys
import time
import webbrowser

REDIS_HOST = "localhost"
REDIS_PORT = 6379

BASE_URL = "http://127.0.0.1:8000"

ROUTES = {
    "1": ("Queue", f"{BASE_URL}/queue"),
    "2": ("Published", f"{BASE_URL}/published"),
    "3": ("Failed", f"{BASE_URL}/failed"),
    "4": ("Engagement", f"{BASE_URL}/engagement"),
}

FUNCTIONS = {
    "5": (
        "Run ingest + draft generation",
        [
            sys.executable,
            "-c",
            (
                "from ingest.sources import save_raw_items; "
                "from llm.draft import generate_for_unprocessed; "
                "save_raw_items(); "
                "generate_for_unprocessed()"
            ),
        ],
    ),
    "6": (
        "Run ingest only",
        [
            sys.executable,
            "-c",
            (
                "from ingest.sources import save_raw_items; "
                "save_raw_items()"
            ),
        ],
    ),
    "7": (
        "Generate drafts only",
        [
            sys.executable,
            "-c",
            (
                "from llm.draft import generate_for_unprocessed; "
                "generate_for_unprocessed()"
            ),
        ],
    ),
}


def check_redis():
    """Verify that Redis is available before starting the application."""
    try:
        with socket.create_connection(
            (REDIS_HOST, REDIS_PORT),
            timeout=2,
        ) as connection:
            connection.sendall(
                b"*1\r\n$4\r\nPING\r\n"
            )

            if not connection.recv(64).startswith(b"+PONG"):
                raise RuntimeError(
                    "Redis did not respond to PING"
                )

        print("✓ Redis connected")

    except Exception as exc:
        print(
            f"✗ Redis is not available: {exc}"
        )
        print(
            "Start Redis before running media_bot."
        )
        sys.exit(1)


def start_processes():
    """Start the dashboard and publishing worker."""

    processes = []

    try:
        print("Starting publisher worker...")

        worker = subprocess.Popen(
            [
                sys.executable,
                "worker.py",
            ]
        )

        processes.append(worker)

        print("Starting FastAPI dashboard...")

        uvicorn = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "dashboard.routes:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ]
        )

        processes.append(uvicorn)

        print()
        print("media_bot running")
        print(
            f"Dashboard: {BASE_URL}/queue"
        )
        print()

        time.sleep(2)

        menu_loop(processes)

    except KeyboardInterrupt:
        print(
            "\nStopping media_bot..."
        )

    finally:
        stop_processes(processes)


def menu_loop(processes):
    """Interactive launcher menu."""

    while True:
        print()
        print("=" * 50)
        print("media_bot menu")
        print("=" * 50)

        print()
        print("Templates / pages")
        print("1. Open Queue")
        print("2. Open Published")
        print("3. Open Failed")
        print("4. Open Engagement")

        print()
        print("Functions")
        print("5. Run ingest + draft generation")
        print("6. Run ingest only")
        print("7. Generate drafts only")

        print()
        print("Utilities")
        print("8. Open FastAPI docs")
        print("9. Check Redis")
        print("10. Open dashboard root")
        print("0. Stop media_bot")

        print()

        choice = input(
            "Select option: "
        ).strip()

        if choice in ROUTES:
            name, url = ROUTES[choice]

            print(
                f"Opening {name}: {url}"
            )

            webbrowser.open(url)

        elif choice in FUNCTIONS:
            name, command = FUNCTIONS[choice]

            print()
            print(
                f"Running: {name}"
            )

            subprocess.run(
                command,
                check=False,
            )

        elif choice == "8":
            webbrowser.open(
                f"{BASE_URL}/docs"
            )

        elif choice == "9":
            check_redis()

        elif choice == "10":
            webbrowser.open(
                BASE_URL
            )

        elif choice == "0":
            print(
                "Stopping media_bot..."
            )
            return

        else:
            print(
                "Unknown option."
            )

        # Catch child-process failures.
        for process in processes:
            if process.poll() is not None:
                raise RuntimeError(
                    "Child process exited "
                    f"with code {process.returncode}"
                )


def stop_processes(processes):
    """Shut down child processes cleanly."""

    for process in processes:
        if process.poll() is None:
            process.terminate()

    for process in processes:
        try:
            process.wait(
                timeout=5
            )

        except subprocess.TimeoutExpired:
            process.kill()

    print("Stopped.")


def main():
    check_redis()
    start_processes()


if __name__ == "__main__":
    main()