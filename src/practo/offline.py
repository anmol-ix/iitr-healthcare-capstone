"""Test-only outbound network tripwire. Allows loopback API/WebSocket tests."""
from contextlib import contextmanager
import ipaddress
import socket
from unittest.mock import patch


def is_local(host):
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


@contextmanager
def offline_guard():
    attempts = []
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    original_dns = socket.getaddrinfo

    def check(address):
        if isinstance(address,tuple) and not is_local(address[0]):
            attempts.append({"host":str(address[0]),"port":address[1]})
            raise RuntimeError("Outbound network forbidden in graded MOCK_LLM execution")

    def connect(sock,address):
        check(address)
        return original_connect(sock,address)

    def connect_ex(sock,address):
        check(address)
        return original_connect_ex(sock,address)

    def dns(host,*args,**kwargs):
        if host is not None and not is_local(host):
            attempts.append({"host":str(host),"operation":"DNS"})
            raise RuntimeError("External DNS forbidden in graded MOCK_LLM execution")
        return original_dns(host,*args,**kwargs)

    with patch.object(socket.socket,"connect",connect), patch.object(socket.socket,"connect_ex",connect_ex), patch.object(socket,"getaddrinfo",dns):
        yield attempts
