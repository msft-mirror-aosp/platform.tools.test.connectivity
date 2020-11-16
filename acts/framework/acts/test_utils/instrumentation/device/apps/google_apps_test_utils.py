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

from acts.test_utils.instrumentation.device.apps.app_installer import \
    AppInstaller
from acts.test_utils.instrumentation.device.command.instrumentation_command_builder \
    import InstrumentationCommandBuilder

ACTIVITY = '.FinskyInstrumentation'


class GoogleAppsTestUtils(object):
    """Utility for managing operations regarding the GoogleAppsTestUtils.apk."""
    def __init__(self, dut, util_apk):
        self._dut = dut
        self._google_apps_test_utils_apk = AppInstaller(dut, util_apk)

    def prevent_playstore_auto_updates(self):
        """Prevents the playstore from auto updating."""
        self._dut.log.info('Preventing playstore from auto updating.')
        if not self._google_apps_test_utils_apk.is_installed():
            self._google_apps_test_utils_apk.install('-g')

        cmd_builder = InstrumentationCommandBuilder()
        cmd_builder.set_manifest_package(self._google_apps_test_utils_apk.pkg_name)
        cmd_builder.set_runner(ACTIVITY)
        cmd_builder.add_flag('-w')
        cmd_builder.add_flag('-r')
        cmd_builder.add_key_value_param('command', 'auto_update')
        cmd_builder.add_key_value_param('value', 'false')
        self._dut.adb.shell(cmd_builder.build())

    def close(self):
        """Clean up util by uninstalling the APK."""
        self._google_apps_test_utils_apk.uninstall()
