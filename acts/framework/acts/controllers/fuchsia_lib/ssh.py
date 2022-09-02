#!/usr/bin/env python3
#
#   Copyright 2022 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0SSHResults
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import paramiko
import paramiko.channel
import socket

from contextlib import contextmanager
from typing import Iterator

from acts import logger
from acts import signals

DEFAULT_SSH_USER: str = "fuchsia"
DEFAULT_SSH_PORT: int = 22
DEFAULT_SSH_TIMEOUT_SEC: int = 30


class FuchsiaSSHError(signals.TestError):
    """A SSH command returned with a non-zero status code."""

    def __init__(self, command, result):
        super().__init__(
            f'SSH command "{command}" unexpectedly returned {result}')
        self.result = result


class FuchsiaSSHTransportError(signals.TestError):
    """Failure to send an SSH command."""
    pass


class SSHResults:
    """Results from an SSH command."""

    _raw_stdout: bytes
    _stdout: str
    _stderr: str
    _exit_status: int

    def __init__(self, stdout: paramiko.channel.ChannelFile,
                 stderr: paramiko.channel.ChannelStderrFile):
        """Create SSHResults from paramiko channels."""
        self._raw_stdout = stdout.read()
        self._stdout = self._raw_stdout.decode('utf-8', errors='replace')
        self._stderr = stderr.read().decode('utf-8', errors='replace')
        self._exit_status = stdout.channel.recv_exit_status()

    def __str__(self):
        if self.exit_status == 0:
            return self.stdout
        return f'status {self.exit_status}, stdout: "{self.stdout}", stderr: "{self.stderr}"'

    @property
    def stdout(self) -> bytes:
        return self._stdout

    @property
    def stderr(self) -> str:
        return self._stderr

    @property
    def exit_status(self) -> int:
        return self._exit_status

    @property
    def raw_stdout(self) -> str:
        return self._raw_stdout


class SSHProvider:
    """Device-specific provider for SSH clients."""

    def __init__(self,
                 ip: str,
                 port: int,
                 private_key_file_name: str,
                 timeout_sec: int = DEFAULT_SSH_TIMEOUT_SEC):
        """
        Args:
            ip: IP used by the SSH server on the device.
            port: Port running the SSH server on the device.
            private_key_file_name: File name of the SSH private key to use.
            timeout_sec: Timeout to connect to the SSH server.
        """
        logger_tag = f"ssh | {ip}"
        if port != DEFAULT_SSH_PORT:
            logger_tag += f':{port}'

        self.log = logger.create_tagged_trace_logger(logger_tag)
        self.ip = ip
        self.port = port
        self.private_key_file_name = private_key_file_name
        self.timeout_sec = timeout_sec

    def run(self,
            command: str,
            timeout_sec: int = DEFAULT_SSH_TIMEOUT_SEC,
            connect_retries: int = 3,
            skip_status_code_check: bool = False) -> SSHResults:
        """Run a command on the device then exit.

        Args:
            command: String to send to the device.
            timeout_sec: Seconds to wait for the command to complete.
            connect_retries: Amount of times to retry connect on fail.
            skip_status_code_check: Whether to check for an error status code.

        Raises:
            FuchsiaSSHError: if the SSH command returns a non-zero status code
                and skip_status_code_check is False
            FuchsiaSSHTransportError: if SSH fails to run the command

        Returns:
            SSHResults from the executed command.
        """
        with self._client(connect_retries) as c:
            try:
                _, stdout, stderr = c.exec_command(command,
                                                   timeout=timeout_sec)
                result = SSHResults(stdout, stderr)
            except Exception as e:
                raise FuchsiaSSHTransportError(
                    f'Failed sending SSH command "{command}"') from e

        if result.exit_status != 0 and not skip_status_code_check:
            raise FuchsiaSSHError(command, result)

        return result

    @contextmanager
    def _client(self, connect_retries: int) -> Iterator[paramiko.SSHClient]:
        """Create a SSH client to the device.

        Args:
            connect_retries: Amount of times to retry connect on fail.

        Returns:
            A context manager around a paramiko.SSHClient that has already been
            connected to the device.
        """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self._connect(client, connect_retries)
            yield client
        finally:
            client.close()

    def _connect(self, client: paramiko.SSHClient, retries: int) -> None:
        """Connect the client to the device.

        Args:
            client: Paramiko SSH client
            retries: Amount of times to retry on fail.
        """
        err: Exception = None
        for i in range(0, retries):
            try:
                client.connect(hostname=self.ip,
                               username=DEFAULT_SSH_USER,
                               allow_agent=False,
                               key_filename=self.private_key_file_name,
                               port=self.port,
                               timeout=self.timeout_sec,
                               auth_timeout=self.timeout_sec,
                               banner_timeout=self.timeout_sec)
                client.get_transport().set_keepalive(1)
                return
            except FileNotFoundError as e:
                raise signals.TestAbortClass('Private key not found') from e
            except (paramiko.SSHException, paramiko.AuthenticationException,
                    socket.timeout, socket.error, ConnectionRefusedError,
                    ConnectionResetError) as e:
                err = e
                self.log.warn(f'Connect failed: {e}')
        raise err
