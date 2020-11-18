#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
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

from acts_contrib.test_utils.instrumentation.device.apps.dismiss_dialogs import \
  DialogDismissalUtil
from acts_contrib.test_utils.instrumentation.power import instrumentation_power_test
from acts_contrib.test_utils.instrumentation.device.command.adb_commands import common


BIG_FILE_PUSH_TIMEOUT = 600

class ChromeTest(instrumentation_power_test.InstrumentationPowerTest):
  """Test class for running chrome cached pages tests."""

  def _prepare_device(self):
    super()._prepare_device()
    self.base_device_configuration()

    self._dialog_util = DialogDismissalUtil(
        self.ad_dut, self.get_file_from_config('dismiss_dialogs_apk')
    )
    self._dialog_util.dismiss_dialogs('Chrome')

  def test_local_chrome_full_sites(self):
    """Measures power when a device loads cached pages on chrome."""
    self.push_to_external_storage(
        self.get_file_from_config('cached_pages'),
        dest = 'Android/data/com.android.chrome',
        timeout = BIG_FILE_PUSH_TIMEOUT)
    self.trigger_scan_on_external_storage()

    sites_params = [
        ('browser_site_delay_in_seconds', 20),
        ('iterations', 1),
        ('url_1',
         'file:///sdcard/Android/data/com.android.chrome/cached_pages/amazon.html'),
        ('url_2',
         'file:///sdcard/Android/data/com.android.chrome/cached_pages/msn.html'),
        ('url_3',
         'file:///sdcard/Android/data/com.android.chrome/cached_pages/cnn.html'),
        ('url_4',
         'file:///sdcard/Android/data/com.android.chrome/cached_pages/espn.html'),
        ('url_5',
         'file:///sdcard/Android/data/com.android.chrome/cached_pages/yahoo.html'),
    ]

    metrics = self.run_and_measure(
        'com.google.android.platform.powertests.ChromeTests',
        'testFullSites',
        extra_params = sites_params)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  def test_local_chrome_full_sites_no_scroll_wifi(self):
    """Measures power when a device loads pages through wifi network."""
    self.adb_run(common.wifi.toggle(True))
    sites_params = [
        ('browser_site_delay_in_seconds', 40),
        ('url_1',
         'http://146.148.91.8/amazon/index.html'),
        ('url_2',
         'http://146.148.91.8/msn/index.html'),
        ('url_3',
         'http://146.148.91.8/cnn/index.html'),
        ('url_4',
         'http://146.148.91.8/espn/index.html'),
        ('url_5',
         'http://146.148.91.8/yahoo/index.html'),
    ]

    metrics = self.run_and_measure(
        'com.google.android.platform.powertests.ChromeTests',
        'testFullSitesNoScroll',
        extra_params = sites_params)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)
