#!/usr/bin/env python3
#
#   Copyright 2021 - The Android Open Source Project
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

import typing
if typing.TYPE_CHECKING:
    from acts.controllers.fuchsia_device import FuchsiaDevice


class FuchsiaSessionManagerLib():
    def __init__(self, fuchsia_device):
        self.device: FuchsiaDevice = fuchsia_device

    def startSession(self):
        """Start a session

        Returns:
            Dictionary:
                error: None, unless an error occurs
                result: 'Success' or None if error
        """
        try:
            # This only works on smart displays, not workstation -- needs a different URL on workstation
            self.device.ffx.run(
                "session launch fuchsia-pkg://fuchsia.com/smart_session#meta/smart_session.cm")
            return {'error': None, 'result': 'Success'}
        except Exception as e:
            return {'error': e, 'result': None}

    def stopSession(self):
        """Stop the session

        Returns:
            Dictionary:
                error: None, unless an error occurs
                result: 'Success', None if error
        """
        result = self.device.ffx.run(
            "component destroy /core/session-manager/session:session",
            skip_status_code_check=True)

        if result.returncode == 0:
            return {'error': None, 'result': 'Success'}
        else:
            if b"InstanceNotFound" in result.stderr or b"instance was not found" in result.stderr:
                return {'error': None, 'result': 'NoSessionToStop'}
            else:
                return {'error': result, 'result': None}
