#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import atexit
import logging
import re
import tempfile
import time

from enum import Enum

from acts.libs.proc import process


class BitsServiceError(Exception):
    pass


class BitsServiceStates(Enum):
    NOT_STARTED = 'not-started'
    STARTED = 'started'
    STOPPED = 'stopped'


class BitsService(object):
    """Helper class to start and stop a bits service

    Attributes:
        port: When the service starts the port it was assigned to is made
        available for external agents to reference to the background service.
    """

    def __init__(self, config_path, binary, output_log_path, timeout=None):
        """Creates a BitsService object.

        Args:
            config_path: Path to a configuration file for the bits_service as
            described in go/pixel-bits/user-guide/service/configuration.md
            binary: Path to a bits_service binary.
            output_log_path: Full path to where the resulting logs should be
            stored.
            timeout: Maximum time in seconds the service should be allowed
            to run in the background after start. If left undefined the service
            in the background will not time out.
        """
        self.port = None
        self._timeout = timeout
        self._binary = binary
        self._config_path = config_path
        self._log = logging.getLogger()
        self._process = None
        self._output_log = open(output_log_path, 'w')
        self._collections_dir = tempfile.TemporaryDirectory(
            prefix='bits_service_collections_dir_')
        self._bits_service_state = BitsServiceStates.NOT_STARTED
        atexit.register(self._cleanup)

    def _cleanup(self):
        self.port = None
        self._collections_dir.cleanup()
        self._output_log.close()
        if self._process and self._process.is_running():
            self._process.stop()

    def _service_started_listener(self, line):
        if self._bits_service_state is BitsServiceStates.STARTED:
            return
        if 'Started server!' in line and self.port is not None:
            self._bits_service_state = BitsServiceStates.STARTED

    PORT_PATTERN = re.compile(r'.*Server listening on .*:(\d+)\.$')

    def _service_port_listener(self, line):
        if self.port is not None:
            return
        match = self.PORT_PATTERN.match(line)
        if match:
            self.port = match.group(1)

    def _output_callback(self, line):
        self._output_log.write(line)
        self._output_log.write('\n')
        self._service_port_listener(line)
        self._service_started_listener(line)

    def _trigger_background_process(self, binary):
        cmd = [binary,
               '--verbosity',
               'debug',
               '--port',
               '0',
               '--collections_folder',
               self._collections_dir.name,
               '--collector_config_file',
               self._config_path]

        # bits_service only works on linux systems, therefore is safe to assume
        # that 'timeout' will be available.
        if self._timeout:
            cmd = ['timeout',
                   '--signal=SIGTERM',
                   str(self._timeout),
                   '--kill-after=60'] + cmd

        self._process = process.Process(cmd)
        self._process.set_on_output_callback(self._output_callback)
        self._process.set_on_terminate_callback(self._on_terminate)
        self._process.start()

    def _on_terminate(self, *_):
        self._log.error('bits_service stopped unexpectedly.')
        self._cleanup()

    def start(self):
        """Starts the bits service in the background.

        This function blocks until the background service signals that it has
        successfully started. A BitsServiceError is raised if the signal is not
        received.
        """
        if self._bits_service_state is BitsServiceStates.STOPPED:
            raise BitsServiceError('bits_service was already stopped. A stopped'
                                   ' service can not be started again.')

        if self._bits_service_state is BitsServiceStates.STARTED:
            raise BitsServiceError('bits_service has already been started.')

        self._trigger_background_process(self._binary)

        # wait 10 seconds for the service to be ready.
        max_startup_wait = time.time() + 10
        while time.time() < max_startup_wait:
            if self._bits_service_state is BitsServiceStates.STARTED:
                self._log.info('bits_service started on port %s' % self.port)
                return
            time.sleep(0.1)

        self._cleanup()
        raise BitsServiceError('bits_service did not start successfully')

    def stop(self):
        """Stops the bits service."""
        if self._bits_service_state is BitsServiceStates.STOPPED:
            raise BitsServiceError('bits service has already been stopped.')
        self._bits_service_state = 'stopped'
        self._cleanup()
