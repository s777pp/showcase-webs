"""Run the Modal CLI over IPv4 only.

On networks with a broken IPv6 path (for example DNS64/NAT64 addresses like 64:ff9b::...
that never answer), the Modal client tries IPv6 first and fails with TimeoutError while
opening its gRPC channel. This wrapper drops IPv6 results from name resolution and
then runs the normal `modal` command with the same arguments:

    py scripts/modal_ipv4.py deploy modal_upscale.py
    py scripts/modal_ipv4.py app list
"""
import runpy
import socket
import sys

_resolve = socket.getaddrinfo


def _ipv4_first(*args, **kwargs):
    rows = _resolve(*args, **kwargs)
    return [row for row in rows if row[0] == socket.AF_INET] or rows


socket.getaddrinfo = _ipv4_first
sys.argv = ["modal"] + sys.argv[1:]
runpy.run_module("modal", run_name="__main__")
