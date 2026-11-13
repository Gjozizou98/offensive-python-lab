#!/usr/bin/env python3
"""
tcp_client.py - Minimal TCP client for banner grabbing and raw requests.

Based on the TCP client from "Black Hat Python" (2nd ed., ch. 2), extended with:
  - command-line arguments (no hardcoded target)
  - timeouts, so the script never hangs forever
  - clear error messages (closed port, filtered port, DNS failure)
  - banner-grab mode (FTP, SSH, SMTP... speak first)
  - full response reading instead of a single recv()

For authorized testing only (own lab, HTB, loopback).
"""

import argparse
import socket
import sys

DEFAULT_TIMEOUT = 5.0   # seconds
BUFFER_SIZE = 4096      # max bytes read per recv() call


def receive_all(sock: socket.socket) -> bytes:
    """Read until the server closes the connection or the timeout expires.

    TCP is a stream: one recv() may return only part of the response,
    so we keep reading and join the pieces at the end.
    """
    chunks = []
    while True:
        try:
            data = sock.recv(BUFFER_SIZE)
        except socket.timeout:
            break               # nothing more within the timeout: assume we're done
        if not data:
            break               # empty bytes = server closed the connection (FIN)
        chunks.append(data)
    return b"".join(chunks)


def tcp_client(host: str, port: int, payload: bytes | None = None,
               timeout: float = DEFAULT_TIMEOUT) -> bytes:
    """Connect, optionally send a payload, return everything the server sends."""
    # AF_INET = IPv4, SOCK_STREAM = TCP.
    # The "with" block closes the socket automatically (sends FIN), even on errors.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(timeout)          # applies to connect(), send() and recv()
        client.connect((host, port))        # DNS lookup + three-way handshake
        if payload:
            client.sendall(payload)         # unlike send(), keeps going until every byte is sent
        return receive_all(client)


def build_payload(args: argparse.Namespace) -> bytes | None:
    """Turn the CLI options into the bytes to send (None = banner-grab mode)."""
    if args.http:
        # "Connection: close" asks the server to close after responding,
        # so receive_all() ends immediately instead of waiting for the timeout.
        request = (
            f"GET {args.http} HTTP/1.1\r\n"
            f"Host: {args.host}\r\n"
            "User-Agent: tcp_client\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        return request.encode()
    if args.data:
        # The shell passes "\r\n" as two literal characters: convert escapes to real bytes.
        return args.data.encode().decode("unicode_escape").encode("latin-1")
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Minimal TCP client: banner grabbing and raw requests. "
                    "For authorized testing only.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  %(prog)s 10.10.10.5 21                  # grab the FTP banner\n"
            "  %(prog)s www.example.com 80 --http      # HTTP GET /\n"
            "  %(prog)s 10.10.10.5 8080 --http /admin  # HTTP GET /admin\n"
            "  %(prog)s 10.10.10.5 25 -d 'EHLO test\\r\\n'\n"
        ),
    )
    parser.add_argument("host", help="target hostname or IP")
    parser.add_argument("port", type=int, help="target TCP port")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--http", nargs="?", const="/", metavar="PATH",
                      help="send an HTTP GET request (default path: /)")
    mode.add_argument("-d", "--data",
                      help="raw data to send; escapes like \\r\\n are interpreted")
    parser.add_argument("-t", "--timeout", type=float, default=DEFAULT_TIMEOUT,
                        help=f"timeout in seconds (default: {DEFAULT_TIMEOUT})")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)
    target = f"{args.host}:{args.port}"

    try:
        response = tcp_client(args.host, args.port, payload, args.timeout)
    except ConnectionRefusedError:
        print(f"[-] {target} refused the connection (port closed: RST received)", file=sys.stderr)
        return 1
    except socket.timeout:
        print(f"[-] {target} timed out (port filtered or host down)", file=sys.stderr)
        return 1
    except socket.gaierror:
        print(f"[-] Could not resolve hostname: {args.host}", file=sys.stderr)
        return 1
    except OSError as err:
        print(f"[-] Network error on {target}: {err}", file=sys.stderr)
        return 1

    if not response:
        print(f"[*] Connected to {target}, but the server sent nothing.")
        print("    The service may wait for the client to speak first: try --http or --data.")
        return 0

    # errors="replace": banners are not always valid UTF-8, never crash on decoding
    print(response.decode(errors="replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())