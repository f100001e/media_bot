import subprocess
import socket
import sys
import time

REDIS_HOST = "localhost"
REDIS_PORT = 6379


def check_redis():
    """Verify that Redis is available before starting the application."""
    try:
        with socket.create_connection(
            (REDIS_HOST, REDIS_PORT), timeout=2
        ) as connection:
            connection.sendall(b"*1\r\n$4\r\nPING\r\n")
            if not connection.recv(64).startswith(b"+PONG"):
                raise RuntimeError("Redis did not respond to PING")
        print("✓ Redis connected")
    except Exception as exc:
        print(f"✗ Redis is not available: {exc}")
        print("Start Redis before running media_bot.")
        sys.exit(1)


def start_processes():
    """Start the dashboard and publishing worker."""

    processes = []

    try:
        print("Starting publisher worker...")
        worker = subprocess.Popen(
            [sys.executable, "worker.py"]
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
        print("Dashboard: http://localhost:8000")
        print("Press Ctrl+C to stop.")

        while True:
            # Detect if either child unexpectedly dies.
            for process in processes:
                if process.poll() is not None:
                    raise RuntimeError(
                        f"Child process exited with code {process.returncode}"
                    )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping media_bot...")

    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()

        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        print("Stopped.")


def main():
    check_redis()
    start_processes()


if __name__ == "__main__":
    main()