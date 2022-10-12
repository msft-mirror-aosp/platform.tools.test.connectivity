#!/usr/bin/env python3
#
#   Copyright 2018 - The Android Open Source Project
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

from typing import Any, Mapping
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from acts import utils
from acts.libs.proc import job

DEFAULT_SL4F_RESPONSE_TIMEOUT_SEC = 30


class DeviceOffline(Exception):
    """Exception if the device is no longer reachable via the network."""


class SL4FCommandFailed(Exception):
    """A SL4F command to the server failed."""


class BaseLib():

    def __init__(self, addr):
        self.address = addr

    def send_command(
        self,
        cmd: str,
        args: Mapping[str, Any],
        response_timeout: int = DEFAULT_SL4F_RESPONSE_TIMEOUT_SEC
    ) -> Mapping[str, Any]:
        """Builds and sends a JSON command to SL4F server.

        Args:
            cmd: SL4F method name of command.
            args: Arguments required to execute cmd.
            response_timeout: Seconds to wait for a response before
                throwing an exception.

        Returns:
            Response from SL4F server.
        """
        data = json.dumps({
            "jsonrpc": "2.0",
            # id is required by the SL4F server to parse test_data but is not
            # currently used.
            "id": "",
            "method": cmd,
            "params": args
        }).encode("utf-8")

        req = Request(self.address,
                      data=data,
                      headers={
                          "Content-Type": "application/json; charset=utf-8",
                          "Content-Length": len(data),
                      })

        try:
            response = urlopen(req, timeout=response_timeout)
        except TimeoutError as e:
            host = urlparse(self.address).hostname
            if not utils.can_ping(job, host):
                raise DeviceOffline(
                    f'FuchsiaDevice {host} is not reachable via the network.')
            raise e

        response_body = response.read().decode("utf-8")
        try:
            response_json = json.loads(response_body)
        except json.JSONDecodeError as e:
            raise SL4FCommandFailed(response_body) from e

        # If the SL4F command fails it returns a str, without an 'error' field
        # to get.
        if not isinstance(response_json, dict):
            raise SL4FCommandFailed(response_json)

        return response_json
