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

from acts_contrib.test_utils.instrumentation.device.apps.app_installer import \
  AppInstaller

class ModemDiagUtil(object):
  """Class to act as a Modem Diagnostic utility """
  def __init__(self, dut, util_apk):
    self._dut = dut
    self._modem_diag_util_apk = AppInstaller(dut, util_apk)
    self._modem_diag_util_apk.install()

  def cut_band(self, band_to_cut):
    if band_to_cut == 'Band13':
        self._dut.adb.shell("am instrument -w -e request '4B 13 26 00 08 00 00 00 40 00 08 00 0A 00 00 10 00 00 00 00 00 00 2F 6E 76 2F 69 74 65 6D 5F 66 69 6C 65 73 2F 6D 6F 64 65 6D 2F 6D 6D 6F 64 65 2F 6C 74 65 5F 62 61 6E 64 70 72 65 66 00' com.google.mdstest/com.google.mdstest.instrument.ModemCommandInstrumentation")
    elif band_to_cut == 'Band4':
        self._dut.adb.shell("am instrument -w -e request '4B 13 26 00 08 00 00 00 40 00 08 00 0B 00 08 00 00 00 00 00 00 00 2F 6E 76 2F 69 74 65 6D 5F 66 69 6C 65 73 2F 6D 6F 64 65 6D 2F 6D 6D 6F 64 65 2F 6C 74 65 5F 62 61 6E 64 70 72 65 66 00' com.google.mdstest/com.google.mdstest.instrument.ModemCommandInstrumentation")

  def close(self):
    """Clean up util by uninstalling the Google account util APK."""
    self._modem_diag_util_apk.uninstall()
