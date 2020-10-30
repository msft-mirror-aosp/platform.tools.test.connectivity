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

import os
import random
import statistics
import tempfile
import time
import json

from acts import signals
from acts.controllers.android_device import SL4A_APK_NAME
from acts.test_utils.instrumentation.power import instrumentation_power_test
from acts.test_utils.instrumentation.device.command.adb_commands import common
from acts.test_utils.instrumentation.device.command.adb_commands import goog
from acts.test_utils.instrumentation.device.apps.app_installer import AppInstaller
from acts.test_utils.instrumentation.instrumentation_base_test import InstrumentationTestError
from acts.controllers import power_metrics

from enum import Enum

DEFAULT_WAIT_TO_FASTBOOT_MODE = 60
DEFAULT_DEVICE_COOL_DOWN_TIME = 80
DEFAULT_WAIT_FOR_REBOOT = 180
WIFI_SSID = 'TP-Link-VZW-DoU'
GMAIL_ACCOUNT = 'vdou001@gmail.com'


def get_median_current(test_results, test_instance):
  """Returns the median current, or a failure if the test failed."""

  # Look at results within the good range (i.e., passing results).
  valid_results = list(filter(lambda result: isinstance(result, signals.TestPass),
                         test_results))

  # If there is no passing test results check failed test results.
  if not valid_results:
    out_range_results = list(
        filter(lambda result: isinstance(result, signals.TestFailure),
               test_results))
    if not out_range_results:
      return test_results[-1]

    median_current = test_instance.get_median_metric(out_range_results)
    return signals.TestFailure(
        'Failed msg! Current: %s out of range' % median_current,
        extras={'average_current': median_current})
  else:
    median_current = test_instance.get_median_metric(valid_results)
    return signals.TestPass(
        'Pass msg! Current: %s' % median_current,
        extras={'average_current': median_current})


class TestCase(Enum):
    TC25 = 'TC25'
    TC28 = 'TC28'
    TC29 = 'TC29'
    TC34 = 'TC34'


class VzWDoUAutomationBaseTest(
    instrumentation_power_test.InstrumentationPowerTest):
  """Base class that implements common functionality of
  days of use test cases
  """

  def base_device_configuration(self):
    """Runs the adb commands for days of use power testing."""

    self.log.info('Running base adb setup commands.')
    self.ad_dut.adb.ensure_root()
    self.adb_run(common.dismiss_keyguard)
    self.adb_run(goog.location_off_warning_dialog.toggle(False), timeout=120)
    self.adb_run(common.airplane_mode.toggle(False), timeout=120)
    self.adb_run(common.auto_rotate.toggle(False))
    self.set_screen_brightness_level()
    self.adb_run(common.screen_adaptive_brightness.toggle(False))
    self.adb_run(common.modem_diag.toggle(False))
    self.adb_run(common.skip_gesture.toggle(False))
    self.adb_run(common.screensaver.toggle(False))
    self.adb_run(common.doze_pulse_on_pick_up.toggle(False))
    self.adb_run(common.aware_enabled.toggle(False))
    self.adb_run(common.doze_wake_screen_gesture.toggle(False))
    self.adb_run(common.doze_mode.toggle(False))
    self.adb_run(common.doze_always_on.toggle(False))
    self.adb_run(common.silence_gesture.toggle(False))
    self.adb_run(common.single_tap_gesture.toggle(False))
    self.adb_run(goog.location_collection.toggle(False), timeout=120)
    self.adb_run(goog.icing.toggle(False))
    self.adb_run(common.stop_moisture_detection)
    self.adb_run(common.ambient_eq.toggle(False))
    self.adb_run(common.wifi_state.toggle(True))
    self.adb_run('echo 1 > /d/clk/debug_suspend')
    self.adb_run(common.bluetooth.toggle(True))
    self.adb_run(common.enable_full_batterystats_history)
    self.adb_run(goog.disable_playstore)
    self.adb_run(goog.disable_volta)
    # Test harness flag
    harness_prop = 'getprop ro.test_harness'
    # command would fail if properties were previously set, therefore it
    # needs to be verified first
    if self.adb_run(harness_prop)[harness_prop] != '1':
      self.log.info('Enable test harness.')
      self.adb_run('echo ro.test_harness=1 >> /data/local.prop')
      self.adb_run('chmod 644 /data/local.prop')
      self.adb_run(common.test_harness.toggle(True))
    self.adb_run(goog.force_stop_nexuslauncher)
    self.adb_run(common.enable_ramdumps.toggle(False))
    self.adb_run(goog.disable_betterbug)
    self.adb_run('input keyevent 26')
    self.adb_run(common.screen_timeout_ms.set_value(180000))

  def _prepare_device(self):
    """Prepares the device for power testing."""
    self._factory_reset()
    super()._prepare_device()
    self.base_device_configuration()
    self.log_in_gmail_account()
    self._cut_band()

  def _cleanup_device(self):
    super()._cleanup_device()
    self.adb_run('input keyevent 26')

  def teardown_test(self):
    """Test teardown"""
    self.log.info('Teardown test at vzw dou automation base.')
    self.power_monitor.connect_usb()
    super().teardown_test()

  def _factory_reset(self):
    """Factory reset device before testing."""
    self.log.info('Running factory reset.')
    self._sl4a_apk = AppInstaller.pull_from_device(
        self.ad_dut, SL4A_APK_NAME, tempfile.mkdtemp(prefix='sl4a'))
    self.ad_dut.adb.ensure_root()
    self._install_google_account_util_apk()
    self.adb_run(goog.remove_gmail_account)
    self.ad_dut.reboot()
    self.ad_dut.wait_for_boot_completion()
    time.sleep(DEFAULT_WAIT_FOR_REBOOT)
    self.ad_dut.adb.ensure_root()
    self.ad_dut.log.debug('Reboot to bootloader')
    self.ad_dut.stop_services()
    self.ad_dut.adb.reboot('bootloader', ignore_status=True)
    time.sleep(DEFAULT_WAIT_FOR_REBOOT)
    self.fastboot_run('-w')
    self.ad_dut.log.debug('Reboot in fastboot')
    self.ad_dut.fastboot.reboot()
    self.ad_dut.wait_for_boot_completion()
    time.sleep(DEFAULT_WAIT_FOR_REBOOT)
    self.ad_dut.root_adb()
    if not self.ad_dut.is_sl4a_installed() and self._sl4a_apk:
      self._sl4a_apk.install()
    self.ad_dut.start_services()

  def _install_google_account_util_apk(self):
    """Installs google account util apk on the device."""
    _google_account_util_file = self.get_file_from_config(
        'google_account_util_apk')
    self._google_account_util = AppInstaller(self.ad_dut,
                                             _google_account_util_file)
    self._google_account_util.install('-g')
    if not self._google_account_util.is_installed():
      raise InstrumentationTestError(
          'Failed to install google account util APK.')

  def _cut_band(self):
    additional_setting = self._instrumentation_config.get_config('additional_setting')
    band_to_cut = None
    if additional_setting:
      band_to_cut = additional_setting.get('band_to_cut')
    if band_to_cut:
      self.log.info('Cutting band: {}'.format(band_to_cut))
      self.ad_dut.adb.ensure_root()
      lock_band_cmd = ('am instrument -w -r -e lock_band {} -e '
                       'skip_pre_test_conditions TRUE -e '
                       'skip_post_test_conditions TRUE -e class '
                       'com.google.android.platform.dou.MDSSwitchBandTests#testSwitchBand'
                       ' '
                       'com.google.android.platform.dou/androidx.test.runner.AndroidJUnitRunner').format(
          band_to_cut)
      self.adb_run(lock_band_cmd, timeout=480)
      self.ad_dut.reboot()
      self.ad_dut.wait_for_boot_completion()
      time.sleep(DEFAULT_WAIT_FOR_REBOOT)

  def generate_random_ssid(self):
    # Generate random permutations as ssid
    ssid = os.popen('shuf -i 1111111111-9999999999 -n 1').read(10)
    return ssid.strip()

  def push_movies_to_dut(self):
    # Push the movies folder to Android device
    sdcard_movies_path_dut = '/sdcard/Movies/'
    sdcard_movies_path = self.user_params['sdcard_movies_path'][0]
    self.log.info('sdcard_movies_path is %s' % sdcard_movies_path)
    self.ad_dut.adb.push(sdcard_movies_path + '/*', sdcard_movies_path_dut)
    self.ad_dut.reboot()
    self.ad_dut.wait_for_boot_completion()
    time.sleep(DEFAULT_WAIT_FOR_REBOOT)

  def log_in_gmail_account(self, sync='false', wait_for_checkin='false'):
    # Log in to gmail account
    self._install_google_account_util_apk()
    time.sleep(DEFAULT_DEVICE_COOL_DOWN_TIME)
    additional_setting = self._instrumentation_config.get_config('additional_setting')
    gmail_phrase = additional_setting.get('gmail_phrase')
    log_in_cmd = (
        'am instrument -w -e account {} -e '
        'password {} -e sync {} -e wait-for-checkin {} '
        'com.google.android.tradefed.account/.AddAccount'
    ).format(GMAIL_ACCOUNT, gmail_phrase, sync, wait_for_checkin)
    self.log.info('gmail log in commands %s' % log_in_cmd)
    self.adb_run(log_in_cmd, timeout=300)
    time.sleep(DEFAULT_DEVICE_COOL_DOWN_TIME)

  def push_music_to_dut(self):
    # Push the music folder to Android device
    sdcard_music_path_dut = '/sdcard/Music/'
    sdcard_music_path = self.user_params['sdcard_music_path'][0]
    self.log.info('sdcard_music_path is %s' % sdcard_music_path)
    self.ad_dut.adb.push(sdcard_music_path + '/*', sdcard_music_path_dut)
    self.ad_dut.reboot()
    self.ad_dut.wait_for_boot_completion()
    time.sleep(DEFAULT_DEVICE_COOL_DOWN_TIME)

  def generate_random_exchange_email_account(self, test_name: TestCase):
    # Generate random exchange email account based on test case
    if test_name == TestCase.TC25:
      random_num = str(random.randint(1, 25))
      num = random_num.zfill(3)
      email_account = 'pixelvzwdoutouch%s@gtestmailer.com' % num
      self.log.info('TC25 exchange email is %s' % email_account)
    elif test_name == TestCase.TC34:
      random_num = str(random.randint(2, 25))
      num = random_num.zfill(3)
      email_account = 'pixelvzwdoupure%s@gtestmailer.com' % num
      self.log.info('TC34 exchange email is %s' % email_account)
    else:
      random_num = str(random.randint(1, 50))
      num = random_num.zfill(3)
      email_account = 'pixelvzwdou%s@gtestmailer.com' % num
      self.log.info('Exchange email is %s' % email_account)
    return email_account

  def convert_power_metric_dict_to_object(self, power_meric_dict):
    # Convert power metric dict to object
    metric_object_list = []
    for metric in power_meric_dict:
      metric_object = power_metrics.Metric(metric['value'], metric['_unit_type'],
                                           metric['unit'], name=metric['name'])
      metric_object_list.append(metric_object)
    return metric_object_list

  def get_median_metric(self, test_results):
    # Get the median current and median metric from the given test results.
    median_current = statistics.median_low([
        x.extras[list(x.extras.keys())[0]]['avg_current']['actual']
        for x in test_results
    ])
    self.log.debug('The median_current is %s' % median_current)

    # Get the median metrics for test results recording.
    final_metrics = {}
    result_dict_list = []
    key = ''
    for x in test_results:
      key = list(x.extras.keys())[0]
      if str(x.extras[list(
          x.extras.keys())[0]]['avg_current']['actual']) == str(median_current):
        median_metric = x.extras[list(
            x.extras.keys())[0]]['avg_current']['power_metric']
        result_dict_list = json.loads(median_metric)
        self.log.debug('Median metrics result dict list is %s' %
                       result_dict_list)
        key = list(x.extras.keys())[0]
        self.log.debug('The key of the median result dict is %s' % key)
        break

    # Get the median metrics for test results recording.
    self.log.debug('The key of the final_metrics is %s' % key)
    self.log.debug('The result dict list of the final_metrics %s' %
                   result_dict_list)
    result_object_list = self.convert_power_metric_dict_to_object(
        result_dict_list)
    self.log.debug('The result object list of the final_metrics %s' %
                   result_object_list)
    final_metrics[key] = result_object_list

    # Record median metrics.
    self.record_metrics(final_metrics)
    return median_current
