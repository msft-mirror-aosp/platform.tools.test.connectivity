#!/usr/bin/env python3
#
# Copyright 2020 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from acts.test_utils.instrumentation.device.apps.app_installer import \
    AppInstaller
from acts.test_utils.instrumentation.device.command.instrumentation_command_builder \
    import InstrumentationCommandBuilder

DISMISS_DIALOGS_RUNNER = '.DismissDialogsInstrumentation'


class DialogDismissalUtil(object):
    """Utility for dismissing app dialogs."""
    def __init__(self, dut, util_apk):
        self._dut = dut
        self._dismiss_dialogs_apk = AppInstaller(dut, util_apk)
        self._dismiss_dialogs_apk.install()

    def dismiss_dialogs(self, apps):
        """Dismiss dialogs for the given apps.

        Args:
            apps: List of apps to dismiss dialogs
        """
        if not apps:
            return
        self._dut.log.info('Dismissing app dialogs for %s' % apps)
        cmd_builder = InstrumentationCommandBuilder()
        cmd_builder.set_manifest_package(self._dismiss_dialogs_apk.pkg_name)
        cmd_builder.set_runner(DISMISS_DIALOGS_RUNNER)
        cmd_builder.add_flag('-w')
        cmd_builder.add_key_value_param('apps', ','.join(apps))
        self._dut.adb.shell(cmd_builder.build())

    def __del__(self):
        self._dismiss_dialogs_apk.uninstall()
