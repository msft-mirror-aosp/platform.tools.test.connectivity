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

from datetime import datetime
import json
import os
import socket
import subprocess
import time

from acts import context
from acts import logger
from acts import signals
from acts import utils

PM_REPO_URL = "fuchsia.com"
PM_FULL_REPO_URL = "fuchsia-pkg://" + PM_REPO_URL
PM_SERVE_STOP_TIMEOUT_SEC = 5


def random_port():
    s = socket.socket()
    s.bind(('', 0))
    return s.getsockname()[1]


class PackageServer:
    """Package manager for Fuchsia; an interface to the "pm" CLI tool.

    Attributes:
        log: Logger for the device-specific instance of ffx.
        binary_path: Path to the pm binary.
        packages_path: Path to amber-files.
        port: Port to listen on for package serving.
    """

    def __init__(self, binary_path, packages_path):
        """
        Args:
            binary_path: Path to ffx binary.
            packages_path: Path to amber-files.
        """
        self.port = random_port()
        self.log = logger.create_tagged_trace_logger(f"pm")
        self.binary_path = binary_path
        self.packages_path = packages_path

        self._server_log = None
        self._server_proc = None

        self._assert_repo_has_not_expired()

    def _assert_repo_has_not_expired(self):
        """Abort if the repository metadata has expired."""
        with open(f'{self.packages_path}/repository/timestamp.json', 'r') as f:
            data = json.load(f)
            expiresAtRaw = data["signed"]["expires"]
            expiresAt = datetime.strptime(expiresAtRaw, '%Y-%m-%dT%H:%M:%SZ')
            if expiresAt <= datetime.now():
                raise signals.TestAbortClass(
                    f'{self.packages_path}/repository/timestamp.json has expired on {expiresAtRaw}'
                )

    def start(self):
        """Start the package server.

        Does not check for errors; view the log file for any errors.
        """
        if self._server_proc:
            self.log.warn(
                "Skipping to start the server since it has already been started"
            )
            return

        pm_command = f'{self.binary_path} serve -c 2 -repo {self.packages_path} -l :{self.port}'

        root_dir = context.get_current_context().get_full_output_path()
        epoch = utils.get_current_epoch_time()
        time_stamp = logger.normalize_log_line_timestamp(
            logger.epoch_to_log_line_timestamp(epoch))
        self._log_path = os.path.join(root_dir, f'pm_server.{time_stamp}.log')

        self._server_log = open(self._log_path, 'a+')
        self._server_proc = subprocess.Popen(pm_command.split(),
                                             preexec_fn=os.setpgrp,
                                             stdout=self._server_log,
                                             stderr=subprocess.STDOUT)
        self._wait_for_server()
        self.log.info(f'Serving packages on port {self.port}')

    def _wait_for_server(self, timeout_sec=5):
        """Wait for the server to expose the correct port.

        The package server takes some time to start. Call this after launching
        the server to avoid race condition.
        """
        timeout = time.perf_counter() + timeout_sec
        while True:
            try:
                socket.create_connection(('127.0.0.1', self.port),
                                         timeout=timeout)
                return
            except ConnectionRefusedError:
                continue
            except Exception as e:
                # Expected errors should be listed above. This is an unexpected
                # error.
                self.log.error(e)
            finally:
                if time.perf_counter() > timeout:
                    self._server_log.close()
                    with open(self._log_path, 'r') as f:
                        logs = f.read()
                    raise TimeoutError(
                        f"pm serve failed to expose port {self.port} after {timeout_sec}s. Logs:\n{logs}"
                    )

    def stop_server(self):
        """Stop the package server."""
        if not self._server_proc:
            self.log.warn(
                "Skipping to stop the server since it hasn't been started yet")
            return

        self._server_proc.terminate()
        try:
            self._server_proc.wait(timeout=PM_SERVE_STOP_TIMEOUT_SEC)
        except subprocess.TimeoutExpired:
            self.log.warn(
                f"Taking over {PM_SERVE_STOP_TIMEOUT_SEC}s to stop. Killing the server"
            )
            self._server_proc.kill()
            self._server_proc.wait(timeout=PM_SERVE_STOP_TIMEOUT_SEC)
        finally:
            self._server_log.close()

        self._server_proc = None
        self._log_path = None
        self._server_log = None

    def clean_up(self):
        if self._server_proc:
            self.stop_server()
