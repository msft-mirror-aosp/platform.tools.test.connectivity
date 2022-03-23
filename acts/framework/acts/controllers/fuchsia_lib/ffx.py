#!/usr/bin/env python3
#
#   Copyright 2022 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import json
import os
import tempfile

from pathlib import Path

from acts import context
from acts import logger
from acts import signals
from acts.libs.proc import job

FFX_DEFAULT_COMMAND_TIMEOUT = 60


class FFXError(signals.TestError):
    pass


class FFX:
    """Device-specific controller for the ffx tool.

    Attributes:
        log: Logger for the device-specific instance of ffx.
        binary_path: Path to the ffx binary.
        config_path: Path to the ffx configuration JSON file.
        ssh_auth_sock_path: Path to the temporary ssh_auth_sock file.
        overnet_socket_path: Path to the temporary overnet socket file.
    """

    def __init__(self, binary_path, target, ssh_private_key_path=None):
        """
        Args:
            binary_path: Path to ffx binary.
            target: Fuchsia mDNS nodename of default target.
            ssh_private_key_path: Path to SSH private key for talking to the
                Fuchsia DUT.
        """
        self.log = logger.create_tagged_trace_logger(f"ffx | {target}")
        self.binary_path = binary_path

        # Create a new isolated environment for ffx. This is needed to avoid
        # overlapping ffx daemons while testing in parallel, causing the ffx
        # invocations to “upgrade” one daemon to another, which appears as a
        # flap/restart to another test.
        root_dir = context.get_current_context(
            context.ContextLevel.ROOT).get_full_output_path()
        target_dir = os.path.join(root_dir, target)
        ffx_daemon_log_dir = os.path.join(target_dir, "ffx_daemon_logs")

        for dir in [target_dir, ffx_daemon_log_dir]:
            os.makedirs(dir, exist_ok=True)

        # Sockets need to be created in a different directory to be guaranteed
        # to stay under the maximum socket path length of 104 characters.
        # See https://unix.stackexchange.com/q/367008
        self.ssh_auth_sock_path = tempfile.mkstemp(suffix="ssh_auth_sock")[1]
        self.overnet_socket_path = tempfile.mkstemp(suffix="overnet_socket")[1]

        config = {
            "target": {
                "default": target,
            },
            # Use user-specific and device-specific locations for sockets.
            # Avoids user permission errors in a multi-user test environment.
            # Avoids daemon upgrades when running tests in parallel in a CI
            # environment.
            "ssh": {
                "auth-sock": self.ssh_auth_sock_path,
            },
            "overnet": {
                "socket": self.overnet_socket_path,
            },
            # Configure the ffx daemon to log to a place where we can read it.
            # Note, ffx client will still output to stdout, not this log
            # directory.
            "log": {
                "enabled": True,
                "dir": [ffx_daemon_log_dir],
            },
            # Disable analytics to decrease noise on the network.
            "ffx": {
                "analytics": {
                    "disabled": True,
                },
            },
        }

        # ffx looks for the private key in several default locations. For
        # testbeds which have the private key in another location, set it now.
        if ssh_private_key_path:
            config["ssh"]["priv"] = ssh_private_key_path

        self.config_path = os.path.join(target_dir, "ffx_config.json")
        with open(self.config_path, 'w', encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

        # The ffx daemon will started automatically when needed. There is no
        # need to start it manually here.

    def clean_up(self):
        self.run("daemon stop")

        # Remove socket files.
        # TODO(https://fxbug.dev/93599): Replace the for-loop below once labs
        # run Python 3.8 or higher. It should be replaced with:
        # Path(self.ssh_auth_sock_path).unlink(missing_ok=True)
        # Path(self.overnet_socket_path).unlink(missing_ok=True)
        for filename in [self.ssh_auth_sock_path, self.overnet_socket_path]:
            file = Path(filename)
            if file.exists():
                file.unlink()

    def run(self,
            command,
            timeout_sec=FFX_DEFAULT_COMMAND_TIMEOUT,
            skip_status_code_check=False):
        """Runs an ffx command.

        Args:
            command: string, command to run with ffx.
            timeout_sec: Seconds to wait for a command to complete.
            skip_status_code_check: Whether to check for the status code.

        Raises:
            job.TimeoutError: when the command times out.
            Error: when the command returns non-zero and skip_status_code_check is False.
            FFXError: when stderr has contents and skip_status_code_check is False.

        Returns:
            A job.Result object containing the results of the command.
        """
        self.log.debug(f'Running "{command}".')

        full_command = f'{self.binary_path} -c {self.config_path} {command}'
        result = job.run(command=full_command,
                         timeout=timeout_sec,
                         ignore_status=skip_status_code_check)

        if isinstance(result, Exception):
            raise result

        elif not skip_status_code_check and result.stderr:
            self.log.warning(
                f'Ran "{full_command}", exit status {result.exit_status}')
            self.log.warning(f'stdout: {result.stdout}')
            self.log.warning(f'stderr: {result.stderr}')

            raise FFXError(
                f'Error when running "{full_command}": {result.stderr}')

        return result
