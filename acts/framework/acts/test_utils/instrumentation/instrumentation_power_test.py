#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
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

import os
import shutil
import tempfile
import time

import tzlocal
from acts.controllers.android_device import SL4A_APK_NAME
from acts.metrics.loggers.blackbox import BlackboxMappedMetricLogger
from acts.test_utils.instrumentation import instrumentation_proto_parser \
    as proto_parser
from acts.test_utils.instrumentation.adb_command_types import DeviceGServices
from acts.test_utils.instrumentation.adb_command_types import DeviceSetprop
from acts.test_utils.instrumentation.adb_command_types import DeviceSetting
from acts.test_utils.instrumentation.adb_commands import common
from acts.test_utils.instrumentation.adb_commands import goog
from acts.test_utils.instrumentation.app_installer import AppInstaller
from acts.test_utils.instrumentation.brightness import \
    get_brightness_for_200_nits
from acts.test_utils.instrumentation.instrumentation_base_test \
    import InstrumentationBaseTest
from acts.test_utils.instrumentation.instrumentation_base_test \
    import InstrumentationTestError
from acts.test_utils.instrumentation.instrumentation_command_builder import \
    DEFAULT_NOHUP_LOG
from acts.test_utils.instrumentation.instrumentation_command_builder import \
    InstrumentationTestCommandBuilder
from acts.test_utils.instrumentation.instrumentation_proto_parser import \
    DEFAULT_INST_LOG_DIR
from acts.test_utils.instrumentation.power_metrics import Measurement
from acts.test_utils.instrumentation.power_metrics import PowerMetrics

from acts import asserts
from acts import context

ACCEPTANCE_THRESHOLD = 'acceptance_threshold'
AUTOTESTER_LOG = 'autotester.log'
DISCONNECT_USB_FILE = 'disconnectusb.log'
POLLING_INTERVAL = 0.5


class InstrumentationPowerTest(InstrumentationBaseTest):
    """Instrumentation test for measuring and validating power metrics.

    Params:
        metric_logger: Blackbox metric logger used to store test metrics.
        _instr_cmd_builder: Builder for the instrumentation command
    """

    def __init__(self, configs):
        super().__init__(configs)
        self.metric_logger = BlackboxMappedMetricLogger.for_test_class()
        self._test_apk = None
        self._sl4a_apk = None
        self._instr_cmd_builder = None
        self._power_metrics = None

    def setup_class(self):
        super().setup_class()
        self.monsoon = self.monsoons[0]
        self._setup_monsoon()
        self._instr_cmd_builder = self.power_instrumentation_command_builder()

    def _prepare_device(self):
        """Prepares the device for power testing."""
        super()._prepare_device()
        self._cleanup_test_files()
        self.install_test_apk()
        self.grant_permissions()

    def _cleanup_device(self):
        """Clean up device after power testing."""
        if self._test_apk:
            self._test_apk.uninstall()
        self._cleanup_test_files()

    def base_device_configuration(self):
        """Run the base setup commands for power testing."""
        self.log.info('Running base device setup commands.')

        self.ad_dut.adb.ensure_root()

        # Test harness flag
        self.adb_run(common.test_harness.toggle(True))

        # Calling
        self.adb_run(common.disable_dialing.toggle(True))

        # Screen
        self.adb_run(common.screen_adaptive_brightness.toggle(False))
        self.adb_run(common.screen_brightness.set_value(
            get_brightness_for_200_nits(self.ad_dut.model)))
        self.adb_run(common.screen_timeout_ms.set_value(1800000))
        self.adb_run(common.notification_led.toggle(False))
        self.adb_run(common.screensaver.toggle(False))
        self.adb_run(common.wake_gesture.toggle(False))
        self.adb_run(common.doze_mode.toggle(False))

        # Accelerometer
        self.adb_run(common.auto_rotate.toggle(False))

        # Time
        self.adb_run(common.auto_time.toggle(False))
        self.adb_run(common.auto_timezone.toggle(False))
        self.adb_run(common.timezone.set_value(str(tzlocal.get_localzone())))

        # Location
        self.adb_run(common.location_gps.toggle(False))
        self.adb_run(common.location_network.toggle(False))

        # Power
        self.adb_run(common.battery_saver_mode.toggle(False))
        self.adb_run(common.battery_saver_trigger.set_value(0))
        self.adb_run(common.enable_full_batterystats_history)
        self.adb_run(common.disable_doze)

        # Camera
        self.adb_run(DeviceSetprop(
            'camera.optbar.hdr', 'true', 'false').toggle(True))

        # Gestures
        gestures = {
            'doze_pulse_on_pick_up': False,
            'doze_pulse_on_double_tap': False,
            'camera_double_tap_power_gesture_disabled': True,
            'camera_double_twist_to_flip_enabled': False,
            'assist_gesture_enabled': False,
            'assist_gesture_silence_alerts_enabled': False,
            'assist_gesture_wake_enabled': False,
            'system_navigation_keys_enabled': False,
            'camera_lift_trigger_enabled': False,
            'doze_always_on': False,
            'aware_enabled': False,
            'doze_wake_screen_gesture': False,
            'skip_gesture': False,
            'silence_gesture': False
        }
        self.adb_run(
            [DeviceSetting(common.SECURE, k).toggle(v)
             for k, v in gestures.items()])

        # GServices
        self.adb_run(goog.location_collection.toggle(False))
        self.adb_run(goog.cast_broadcast.toggle(False))
        self.adb_run(DeviceGServices(
            'location:compact_log_enabled').toggle(True))
        self.adb_run(DeviceGServices('gms:magictether:enable').toggle(False))
        self.adb_run(DeviceGServices('ocr.cc_ocr_enabled').toggle(False))
        self.adb_run(DeviceGServices(
            'gms:phenotype:phenotype_flag:debug_bypass_phenotype').toggle(True))
        self.adb_run(DeviceGServices(
            'gms_icing_extension_download_enabled').toggle(False))

        # Misc. Google features
        self.adb_run(goog.disable_playstore)
        self.adb_run(goog.disable_volta)
        self.adb_run(goog.disable_chre)
        self.adb_run(goog.disable_musiciq)
        self.adb_run(goog.disable_hotword)

        # Enable clock dump info
        self.adb_run('echo 1 > /d/clk/debug_suspend')

    def _setup_monsoon(self):
        """Set up the Monsoon controller for this testclass/testcase."""
        self.log.info('Setting up Monsoon %s' % self.monsoon.serial)
        monsoon_config = self._get_merged_config('Monsoon')
        self._monsoon_voltage = monsoon_config.get_numeric('voltage', 4.2)
        self.monsoon.set_voltage_safe(self._monsoon_voltage)
        if 'max_current' in monsoon_config:
            self.monsoon.set_max_current(
                monsoon_config.get_numeric('max_current'))

        self.monsoon.usb('on')
        self.monsoon.set_on_disconnect(self._on_disconnect)
        self.monsoon.set_on_reconnect(self._on_reconnect)

        self._disconnect_usb_timeout = monsoon_config.get_numeric(
            'usb_disconnection_timeout', 240)

        self._measurement_args = dict(
            duration=monsoon_config.get_numeric('duration'),
            hz=monsoon_config.get_numeric('frequency'),
            measure_after_seconds=monsoon_config.get_numeric('delay')
        )

    def _on_disconnect(self):
        """Callback invoked by device disconnection from the Monsoon."""
        self.ad_dut.log.info('Disconnecting device.')
        self.ad_dut.stop_services()
        # Uninstall SL4A
        self._sl4a_apk = AppInstaller.pull_from_device(
            self.ad_dut, SL4A_APK_NAME, tempfile.mkdtemp(prefix='sl4a'))
        self._sl4a_apk.uninstall()
        time.sleep(1)

    def _on_reconnect(self):
        """Callback invoked by device reconnection to the Monsoon"""
        # Reinstall SL4A
        if not self.ad_dut.is_sl4a_installed() and self._sl4a_apk:
            self._sl4a_apk.install()
            shutil.rmtree(os.path.dirname(self._sl4a_apk.apk_path))
            self._sl4a_apk = None
        self.ad_dut.start_services()
        # Release wake lock to put device into sleep.
        self.ad_dut.droid.goToSleepNow()
        self.ad_dut.log.info('Device reconnected.')

    def install_test_apk(self):
        """Installs test apk on the device."""
        test_apk_file = self._instrumentation_config.get_file('test_apk')
        self._test_apk = AppInstaller(self.ad_dut, test_apk_file)
        self._test_apk.install('-g')
        if not self._test_apk.is_installed():
            raise InstrumentationTestError('Failed to install test APK.')

    def _cleanup_test_files(self):
        """Remove test-generated files from the device."""
        self.ad_dut.log.info('Cleaning up test generated files.')
        for file_name in [DISCONNECT_USB_FILE, DEFAULT_INST_LOG_DIR,
                          DEFAULT_NOHUP_LOG, AUTOTESTER_LOG]:
            path = os.path.join(
                self.ad_dut.adb.shell('echo $EXTERNAL_STORAGE'), file_name)
            self.adb_run('rm -rf %s' % path)

    # Test runtime utils

    def power_instrumentation_command_builder(self):
        """Return the default command builder for power tests"""
        builder = InstrumentationTestCommandBuilder.default()
        builder.set_manifest_package(self._test_apk.pkg_name)
        builder.set_nohup()
        return builder

    def _wait_for_disconnect_signal(self):
        """Poll the device for a disconnect USB signal file. This will indicate
        to the Monsoon that the device is ready to be disconnected.
        """
        self.log.info('Waiting for USB disconnect signal')
        disconnect_file = os.path.join(
            self.ad_dut.adb.shell('echo $EXTERNAL_STORAGE'),
            DISCONNECT_USB_FILE)
        start_time = time.time()
        while time.time() < start_time + self._disconnect_usb_timeout:
            if self.ad_dut.adb.shell('ls %s' % disconnect_file):
                return
            time.sleep(POLLING_INTERVAL)
        raise InstrumentationTestError('Timeout while waiting for USB '
                                       'disconnect signal.')

    def measure_power(self):
        """Measures power consumption with the Monsoon. See monsoon_lib API for
        details.
        """
        if not hasattr(self, '_measurement_args'):
            raise InstrumentationTestError('Missing Monsoon measurement args.')

        # Start measurement after receiving disconnect signal
        self._wait_for_disconnect_signal()
        power_data_path = os.path.join(
            context.get_current_context().get_full_output_path(), 'power_data')
        self.log.info('Starting Monsoon measurement.')
        self.monsoon.usb('auto')
        measure_start_time = time.time()
        result = self.monsoon.measure_power(
            **self._measurement_args, output_path=power_data_path)
        self.monsoon.usb('on')
        self.log.info('Monsoon measurement complete.')

        # Gather relevant metrics from measurements
        session = self.dump_instrumentation_result_proto()
        self._power_metrics = PowerMetrics(self._monsoon_voltage,
                                           start_time=measure_start_time)
        self._power_metrics.generate_test_metrics(
            PowerMetrics.import_raw_data(power_data_path),
            proto_parser.get_test_timestamps(session))
        self._log_metrics()
        return result

    def run_and_measure(self, instr_class, instr_method=None, req_params=None):
        """Convenience method for setting up the instrumentation test command,
        running it on the device, and starting the Monsoon measurement.

        Args:
            instr_class: Fully qualified name of the instrumentation test class
            instr_method: Name of the instrumentation test method
            req_params: List of required parameter names

        Returns: summary of Monsoon measurement
        """
        if instr_method:
            self._instr_cmd_builder.add_test_method(instr_class, instr_method)
        else:
            self._instr_cmd_builder.add_test_class(instr_class)
        params = {}
        instr_call_config = self._get_merged_config('instrumentation_call')
        # Add required parameters
        for param_name in req_params or []:
            params[param_name] = instr_call_config.get(
                param_name, verify_fn=lambda x: x is not None,
                failure_msg='%s is a required parameter.' % param_name)
        # Add all other parameters
        params.update(instr_call_config)
        for name, value in params.items():
            self._instr_cmd_builder.add_key_value_param(name, value)
        instr_cmd = self._instr_cmd_builder.build()
        self.log.info('Running instrumentation call: %s' % instr_cmd)
        self.adb_run_async(instr_cmd)
        return self.measure_power()

    def _log_metrics(self):
        """Record the collected metrics with the metric logger."""
        for metric_name in PowerMetrics.ALL_METRICS:
            for instr_test_name in self._power_metrics.test_metrics:
                metric_value = getattr(
                    self._power_metrics.test_metrics[instr_test_name],
                    metric_name).value
                self.metric_logger.add_metric(
                    '%s__%s' % (metric_name, instr_test_name), metric_value)

    def validate_power_results(self, *instr_test_names):
        """Compare power measurements with target values and set the test result
        accordingly.

        Args:
            instr_test_names: Name(s) of the instrumentation test method.
                If none specified, defaults to all test methods run.

        Raises:
            signals.TestFailure if one or more metrics do not satisfy threshold
        """
        summaries = {}
        failures = {}
        all_thresholds = self._get_merged_config(ACCEPTANCE_THRESHOLD)

        if not instr_test_names:
            instr_test_names = all_thresholds.keys()

        for instr_test_name in instr_test_names:
            try:
                test_metrics = self._power_metrics.test_metrics[instr_test_name]
            except KeyError:
                raise InstrumentationTestError(
                    'Unable to find test method %s in instrumentation output. '
                    'Check instrumentation call results in '
                    'instrumentation_proto.txt.'
                    % instr_test_name)

            summaries[instr_test_name] = test_metrics.summary
            failures[instr_test_name] = {}
            test_thresholds = all_thresholds.get_config(instr_test_name)
            for metric_name, metric in test_thresholds.items():
                try:
                    actual_result = getattr(test_metrics, metric_name)
                except AttributeError:
                    continue

                if 'unit_type' not in metric or 'unit' not in metric:
                    continue
                unit_type = metric['unit_type']
                unit = metric['unit']

                lower_value = metric.get_numeric('lower_limit', float('-inf'))
                upper_value = metric.get_numeric('upper_limit', float('inf'))
                if 'expected_value' in metric and 'percent_deviation' in metric:
                    expected_value = metric.get_numeric('expected_value')
                    percent_deviation = metric.get_numeric('percent_deviation')
                    lower_value = expected_value * (1 - percent_deviation / 100)
                    upper_value = expected_value * (1 + percent_deviation / 100)

                lower_bound = Measurement(lower_value, unit_type, unit)
                upper_bound = Measurement(upper_value, unit_type, unit)
                if not lower_bound <= actual_result <= upper_bound:
                    failures[instr_test_name][metric_name] = {
                        'expected': '[%s, %s]' % (lower_bound, upper_bound),
                        'actual': str(actual_result.to_unit(unit))
                    }
        self.log.info('Summary of measurements: %s' % summaries)
        asserts.assert_false(
            any(failures.values()),
            msg='One or more measurements do not meet the specified criteria',
            extras=failures)
