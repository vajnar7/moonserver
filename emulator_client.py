import argparse
import time

import queue_manager


def send_command(command_queue, response_queue, command, timeout=5.0):
    command_queue.put(command)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = response_queue.get(timeout=0.5)
        except Exception:
            continue
        print("Emulator response:", response)
        return
    print("No emulator response received within timeout.")


def main():
    parser = argparse.ArgumentParser(description="Send commands directly to the I/O emulator via queue manager.")
    subparsers = parser.add_subparsers(dest="action")

    connect_parser = subparsers.add_parser("connect", help="Send a connect command to the emulator.")
    connect_parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for response.")

    move_parser = subparsers.add_parser("move", help="Send a move command to the emulator.")
    move_parser.add_argument("distance", type=int, help="Distance for move command.")
    move_parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for response.")

    watch_parser = subparsers.add_parser("watch", help="Monitor emulator responses from the queue.")
    watch_parser.add_argument("--duration", type=float, default=30.0, help="Seconds to watch responses.")

    args = parser.parse_args()
    if args.action is None:
        parser.print_help()
        return

    try:
        command_queue, response_queue = queue_manager.connect_to_manager()
    except Exception as exc:
        print(f"Failed to connect to queue manager: {exc}")
        return

    if args.action == "connect":
        send_command(command_queue, response_queue, {"type": "connect"}, timeout=args.timeout)
    elif args.action == "move":
        send_command(command_queue, response_queue, {"type": "move", "distance": args.distance}, timeout=args.timeout)
    elif args.action == "watch":
        deadline = time.time() + args.duration
        print(f"Watching emulator responses for {args.duration} seconds...")
        while time.time() < deadline:
            try:
                response = response_queue.get(timeout=0.5)
            except Exception:
                continue
            print("Emulator response:", response)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
