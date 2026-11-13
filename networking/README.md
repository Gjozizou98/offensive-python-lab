# tcp_client.py

A lightweight TCP client for **banner grabbing** and **raw protocol requests** during reconnaissance and service enumeration.

Built on the TCP client from *Black Hat Python* (2nd ed., ch. 2) and extended for real-world use: command-line arguments, timeouts, full response handling and readable error messages.

> **For authorized testing only.** Use it on your own lab, Hack The Box / similar platforms, or systems you have written permission to test.

---

## Features

| Feature | Why it matters |
|---|---|
| Banner grabbing | Identify the software and version behind an open port (FTP, SSH, SMTP...) |
| HTTP mode | Send a well-formed `GET` request with the correct `Host` header (virtual hosts) |
| Raw data mode | Speak any text-based protocol by hand, with `\r\n` escapes interpreted |
| Timeouts | The script never hangs on filtered ports or silent services |
| Full response reading | Loops on `recv()` instead of truncating the response at 4096 bytes |
| Clear errors | Distinguishes closed ports, filtered ports and DNS failures |

## Requirements

- Python 3.10+
- Standard library only (no external dependencies)

## Usage

```
python3 tcp_client.py HOST PORT [--http [PATH] | -d DATA] [-t TIMEOUT]
```

| Argument | Description |
|---|---|
| `HOST` | Target hostname or IP address |
| `PORT` | Target TCP port |
| `--http [PATH]` | Send an HTTP `GET` request (default path: `/`) |
| `-d`, `--data DATA` | Send raw data; escape sequences such as `\r\n` are interpreted |
| `-t`, `--timeout SEC` | Connection and read timeout in seconds (default: `5`) |
| `-h`, `--help` | Show help and examples |

`--http` and `--data` are mutually exclusive. With neither, the client runs in **banner-grab mode**: it connects and only listens.

## Examples

**Grab a service banner** (protocols where the server speaks first):

```bash
python3 tcp_client.py 10.10.10.5 21
# 220 (vsFTPd 3.0.3)

python3 tcp_client.py 10.10.10.5 22
# SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6
```

**Send an HTTP request:**

```bash
python3 tcp_client.py 10.10.10.5 80 --http
python3 tcp_client.py 10.10.10.5 8080 --http /admin
```

**Talk to a protocol by hand** (here, SMTP):

```bash
python3 tcp_client.py 10.10.10.5 25 -d 'EHLO test\r\n'
```

**Faster checks on many hosts** with a shorter timeout:

```bash
python3 tcp_client.py 10.10.10.5 3306 -t 2
```

## Error messages

| Message | Meaning |
|---|---|
| `refused the connection (port closed: RST received)` | The host is up but nothing listens on that port |
| `timed out (port filtered or host down)` | No answer at all: a firewall drops the packets, or the host is offline |
| `Could not resolve hostname` | DNS lookup failed: check the name or add it to `/etc/hosts` |
| `Connected ... but the server sent nothing` | The service waits for the client to speak first: retry with `--http` or `--data` |

Exit code is `0` on success and `1` on any network error, so the tool can be used in shell scripts.

## How it works

```
socket()  ->  connect()  ->  sendall()  ->  recv() loop  ->  close()
              handshake      optional       until FIN        automatic
              SYN/SYN-ACK/ACK  payload      or timeout       ("with" block)
```

1. Creates an IPv4 TCP socket (`AF_INET`, `SOCK_STREAM`) and sets a timeout.
2. `connect()` resolves the hostname and performs the three-way handshake.
3. If a payload is given, `sendall()` sends every byte of it.
4. `recv()` is called in a loop, because TCP is a byte stream and a single read may return only part of the response. The loop stops when the server closes the connection or the timeout expires.
5. The `with` block closes the socket automatically, even if an error occurs.

**Note on banner-grab mode:** services like FTP or SSH keep the connection open after sending the banner, so the client waits for the full timeout before printing. Use `-t 2` to speed it up. In HTTP mode the request includes `Connection: close`, so the server closes immediately after responding.

## Detection (blue team view)

- Each run creates a full TCP connection that appears in firewall and service logs.
- Banner-grab connections that send no data and disconnect are a common recon signature.
- The HTTP mode sends `User-Agent: tcp_client`, which is easy to spot in web server logs.

## Disclaimer

This tool is intended for educational purposes and authorized security testing only. The author is not responsible for misuse.