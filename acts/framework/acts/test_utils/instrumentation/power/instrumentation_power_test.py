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
from acts import asserts
from acts import context
from acts.controllers import monsoon as monsoon_controller
from acts.controllers import power_monitor as power_monitor_lib
from acts.controllers.android_device import SL4A_APK_NAME
from acts.metrics.loggers.blackbox import BlackboxMappedMetricLogger
from acts.metrics.loggers.bounded_metrics import BoundedMetricsLogger
from acts.test_utils.instrumentation import instrumentation_proto_parser as proto_parser
from acts.test_utils.instrumentation.device.apps.app_installer import AppInstaller
from acts.test_utils.instrumentation.device.apps.permissions import PermissionsUtil
from acts.test_utils.instrumentation.device.command.adb_commands import common
from acts.test_utils.instrumentation.device.command.adb_commands import goog
from acts.test_utils.instrumentation.device.command.instrumentation_command_builder import DEFAULT_INSTRUMENTATION_LOG_OUTPUT
from acts.test_utils.instrumentation.device.command.instrumentation_command_builder import InstrumentationTestCommandBuilder
from acts.test_utils.instrumentation.instrumentation_base_test import InstrumentationBaseTest
from acts.test_utils.instrumentation.instrumentation_base_test import InstrumentationTestError
from acts.test_utils.instrumentation.instrumentation_proto_parser import DEFAULT_INST_LOG_DIR
from acts.test_utils.instrumentation.power.power_metrics import AbsoluteThresholds

ACCEPTANCE_THRESHOLD = 'acceptance_threshold'
DEFAULT_PUSH_FILE_TIMEOUT = 180
DEFAULT_WAIT_FOR_DEVICE_TIMEOUT = 180
POLLING_INTERVAL = 0.5

AUTOTESTER_LOG = 'autotester.log'
DISCONNECT_USB_FILE = 'disconnectusb.log'
SCREENSHOTS_DIR = 'test_screenshots'

_NETWORK_TYPES = {
    '2g': 1,
    '3g': 0,
    'lte': 12
}


class InstrumentationPowerTest(InstrumentationBaseTest):
    """Instrumentation test for measuring and validating power metrics.

    Params:
        metric_logger: Blackbox metric logger used to store test metrics.
        _instr_cmd_builder: Builder for the instrumentation command
    """

    def __init__(self, configs):
        super().__init__(configs)

        self.blackbox_logger = BlackboxMappedMetricLogger.for_test_case()
        self.bounded_metric_logger = BoundedMetricsLogger.for_test_case()
        self._test_apk = None
        self._sl4a_apk = None
        self._instr_cmd_builder = None
        self.prefer_bits_over_monsoon = False

    def setup_class(self):
        super().setup_class()
        power_monitor_lib.update_registry(self.user_params)
        self.power_monitors = self.pick_power_monitor()
        self.power_monitor = self.power_monitors[0]

    def pick_power_monitor(self):
        there_are_monsoons = hasattr(self, 'monsoons')
        there_are_bitses = hasattr(self, 'bitses')
        asserts.assert_true(there_are_bitses or there_are_monsoons,
                            'at least one power monitor must be defined')
        # use bits if there are bitses defined and is preferred
        # use bits if it is not possible to use monsoons
        use_bits = there_are_bitses and (
            self.prefer_bits_over_monsoon or not there_are_monsoons)
        if use_bits and there_are_monsoons:
            # the monsoon controller interferes with bits.
            monsoon_controller.destroy(self.monsoons)
        if use_bits:
            power_monitors = self.bitses
        else:
            power_monitors = [power_monitor_lib.PowerMonitorMonsoonFacade(
                monsoon) for monsoon in self.monsoons]
        return power_monitors

    def setup_test(self):
        """Test setup"""
        super().setup_test()
        self._setup_power_monitor()
        self._prepare_device()
        self._instr_cmd_builder = self.power_default_instr_command_builder()

    def teardown_test(self):
        """Test teardown"""
        super().teardown_test()
        self.power_monitor.teardown()

    def _prepare_device(self):
        """Prepares the device for power testing."""
        super()._prepare_device()
        self._cleanup_test_files()
        self._permissions_util = PermissionsUtil(
            self.ad_dut,
            self.get_file_from_config('permissions_apk'))
        self._permissions_util.grant_all()
        self._install_test_apk()

    def _cleanup_device(self):
        """Clean up device after power testing."""
        if self._test_apk:
            self._test_apk.uninstall()
        self._permissions_util.close()
        self._pull_test_files()
        self._cleanup_test_files()

    def base_device_configuration(self):
        """Run the base setup commands for power testing."""
        self.log.info('Running base device setup commands.')

        self.ad_dut.adb.ensure_root()
        self.adb_run(common.dismiss_keyguard)
        self.ad_dut.ensure_screen_on()

        # Test harness flag
        harness_prop = 'getprop ro.test_harness'
        # command would fail if properties were previously set, therefore it
        # needs to be verified first
        if self.adb_run(harness_prop)[harness_prop] != '1':
            self.adb_run(common.test_harness.toggle(True))

        # Calling
        disable_dialing_prop = 'getprop ro.telephony.disable-call'
        # command would fail if property was previously set, therefore it needs
        # to be verified first.
        if self.adb_run(disable_dialing_prop)[disable_dialing_prop] != 'true':
            self.adb_run(common.disable_dialing.toggle(True))

        # Screen
        self.adb_run(common.screen_always_on.toggle(True))
        self.adb_run(common.screen_adaptive_brightness.toggle(False))

        brightness_level = None
        if 'brightness_level' in self._instrumentation_config:
            brightness_level = self._instrumentation_config['brightness_level']

        if brightness_level is None:
            raise ValueError('no brightness level defined (or left as None) '
                             'and it is needed.')

        self.adb_run(common.screen_brightness.set_value(brightness_level))
        self.adb_run(common.screen_timeout_ms.set_value(1800000))
        self.adb_run(common.notification_led.toggle(False))
        self.adb_run(common.screensaver.toggle(False))
        self.adb_run(common.wake_gesture.toggle(False))
        self.adb_run(common.doze_mode.toggle(False))
        self.adb_run(common.doze_always_on.toggle(False))
        self.adb_run(common.single_tap_gesture.toggle(False))

        # Sensors
        self.adb_run(common.auto_rotate.toggle(False))
        self.adb_run(common.disable_sensors)
        self.adb_run(common.ambient_eq.toggle(False))

        if self.file_exists(common.MOISTURE_DETECTION_SETTING_FILE):
            self.adb_run(common.disable_moisture_detection)
        self.adb_run(common.stop_moisture_detection)

        # Time
        self.adb_run(common.auto_time.toggle(False))
        self.adb_run(common.auto_timezone.toggle(False))
        self.adb_run(common.timezone.set_value(str(tzlocal.get_localzone())))

        # Location
        self.adb_run(common.location_gps.toggle(False))
        self.adb_run(common.location_network.toggle(False))
        self.adb_run(common.location_mode.toggle(False))

        # Power
        self.adb_run(common.battery_saver_mode.toggle(False))
        self.adb_run(common.battery_saver_trigger.set_value(0))
        self.adb_run(common.enable_full_batterystats_history)
        self.adb_run(common.disable_doze)

        # Camera
        self.adb_run(goog.camera_hdr_mode.toggle(True))

        # Gestures
        self.adb_run(common.doze_pulse_on_pick_up.toggle(False))
        self.adb_run(common.double_tap_gesture.toggle(False))
        self.adb_run(
            common.camera_double_tap_power_gesture_disabled.toggle(True))
        self.adb_run(common.camera_double_twist_to_flip_enabled.toggle(False))
        self.adb_run(goog.edge_sensor.toggle(False))
        self.adb_run(common.system_navigation_keys_enabled.toggle(False))
        self.adb_run(common.camera_lift_trigger_enabled.toggle(False))
        self.adb_run(common.aware_enabled.toggle(False))
        self.adb_run(common.doze_wake_screen_gesture.toggle(False))
        self.adb_run(common.skip_gesture.toggle(False))
        self.adb_run(common.silence_gesture.toggle(False))

        # GServices
        self.adb_run(goog.location_collection.toggle(False))
        self.adb_run(goog.cast_broadcast.toggle(False))
        self.adb_run(goog.compact_location_log.toggle(True))
        self.adb_run(goog.magic_tether.toggle(False))
        self.adb_run(goog.ocr.toggle(False))
        if self._instrumentation_config.get('set_gms_phenotype_flag',
                                            default=True):
            self.adb_run(goog.phenotype.toggle(True))
        self.adb_run(goog.icing.toggle(False))
        self.adb_run(common.disable_pixellogger)

        # Comms
        self.adb_run(common.wifi.toggle(False))
        self.adb_run(common.bluetooth.toggle(False))
        self.adb_run(common.airplane_mode.toggle(True))
        self.adb_run(common.disable_modem)
        self.adb_run(common.nfc.toggle(False))

        # Misc. Google features
        self.adb_run(goog.disable_playstore)
        self.adb_run(goog.disable_volta)
        self.adb_run(goog.disable_chre)
        self.adb_run(goog.disable_musiciq)
        self.adb_run(goog.hotword.toggle(False))

        # Enable clock dump info
        self.adb_run('echo 1 > /d/clk/debug_suspend')

    def _setup_power_monitor(self, **kwargs):
        """Set up the Monsoon controller for this testclass/testcase."""
        monsoon_config = self._get_merged_config('Monsoon')
        self.power_monitor.setup(monsoon_config=monsoon_config)

    def _uninstall_sl4a(self):
        """Stops and uninstalls SL4A if it is available on the DUT"""
        self.ad_dut.log.info('Stopping and uninstalling SL4A if available.')
        self.ad_dut.stop_services()
        # Uninstall SL4A
        self._sl4a_apk = AppInstaller.pull_from_device(
            self.ad_dut, SL4A_APK_NAME, tempfile.mkdtemp(prefix='sl4a'))
        if self._sl4a_apk:
            self._sl4a_apk.uninstall()
        time.sleep(1)

    def _reinstall_sl4a(self):
        """Re-installs and starts SL4A (if it is available)"""
        self.ad_dut.adb.wait_for_device(timeout=DEFAULT_WAIT_FOR_DEVICE_TIMEOUT)
        self.ad_dut.log.debug('device found; allowing 10 seconds for system '
                              'services to start')
        time.sleep(10)
        # Reinstall SL4A
        if not self.ad_dut.is_sl4a_installed() and self._sl4a_apk:
            self._sl4a_apk.install()
            shutil.rmtree(os.path.dirname(self._sl4a_apk.apk_path))
            self._sl4a_apk = None
        self.ad_dut.start_services()

        # Release wake lock to put device into sleep.
        if self.ad_dut.droid:
            self.ad_dut.droid.goToSleepNow()

        self.ad_dut.log.info('SL4A reinstalled and started.')

    def _install_test_apk(self):
        """Installs test apk on the device."""
        test_apk_file = self.get_file_from_config('test_apk')
        self._test_apk = AppInstaller(self.ad_dut, test_apk_file)
        self._test_apk.install('-g')
        if not self._test_apk.is_installed():
            raise InstrumentationTestError('Failed to install test APK.')

    def _pull_test_files(self):
        """Pull test-generated files from the device onto the log directory."""
        dest = self.ad_dut.device_log_path
        self.ad_dut.log.info('Pulling test generated files to %s.' % dest)
        for file_name in [DEFAULT_INSTRUMENTATION_LOG_OUTPUT, SCREENSHOTS_DIR]:
            src = os.path.join(self.ad_dut.external_storage_path, file_name)
            self.ad_dut.pull_files(src, dest)

    def _cleanup_test_files(self):
        """Remove test-generated files from the device."""
        self.ad_dut.log.info('Cleaning up test generated files.')
        for file_name in [DISCONNECT_USB_FILE, DEFAULT_INST_LOG_DIR,
                          DEFAULT_INSTRUMENTATION_LOG_OUTPUT, AUTOTESTER_LOG,
                          SCREENSHOTS_DIR]:
            src = os.path.join(self.ad_dut.external_storage_path, file_name)
            self.adb_run('rm -rf %s' % src)

    def trigger_scan_on_external_storage(self):
        cmd = 'am broadcast -a android.intent.action.MEDIA_MOUNTED '
        cmd = cmd + '-d file://%s ' % self.ad_dut.external_storage_path
        cmd = cmd + '--receiver-include-background'
        return self.adb_run(cmd)

    def push_to_external_storage(self, file_path, dest=None,
                                 timeout=DEFAULT_PUSH_FILE_TIMEOUT):
        """Pushes a file to {$EXTERNAL_STORAGE} and returns its final location.

        Args:
            file_path: The file to be pushed.
            dest: Where within {$EXTERNAL_STORAGE} it should be pushed.
            timeout: Float number of seconds to wait for the file to be pushed.

        Returns: The absolute path where the file was pushed.
        """
        if dest is None:
            dest = os.path.basename(file_path)

        dest_path = os.path.join(self.ad_dut.external_storage_path, dest)
        self.log.info('Clearing %s before pushing %s' % (dest_path, file_path))
        self.ad_dut.adb.shell('rm -rf %s', dest_path)
        self.log.info('Pushing file %s to %s' % (file_path, dest_path))
        self.ad_dut.adb.push(file_path, dest_path, timeout=timeout)
        return dest_path

    def set_preferred_network(self, network_type):
        """Set the preferred network type."""
        self.adb_run(common.airplane_mode.toggle(False))
        self.adb_run(
            common.preferred_network_mode.set_value(
                _NETWORK_TYPES[network_type.lower()]
            )
        )
        self.ad_dut.reboot()
        self.adb_run(common.disable_doze)

    # Test runtime utils

    def power_default_instr_command_builder(self):
        """Return the default command builder for power tests"""
        builder = InstrumentationTestCommandBuilder.default()
        builder.set_manifest_package(self._test_apk.pkg_name)
        builder.add_flag('--no-isolated-storage')
        builder.set_output_as_text()
        builder.set_nohup()
        return builder

    def _wait_for_disconnect_signal(self, disconnect_usb_timeout):
        """Poll the device for a disconnect USB signal file. This will indicate
        to the Monsoon that the device is ready to be disconnected.
        """
        self.log.info('Waiting for USB disconnect signal')
        start_time = time.time()
        disconnect_usb_file = os.path.join(self.ad_dut.external_storage_path,
                                           DISCONNECT_USB_FILE)
        while time.time() < start_time + disconnect_usb_timeout:
            if self.ad_dut.adb.shell('ls %s || true' % disconnect_usb_file):
                self.log.info('Disconnection signal received. File: '
                              '"%s"' % disconnect_usb_file)
                self.ad_dut.pull_files(disconnect_usb_file,
                                       self.ad_dut.device_log_path)
                return
            time.sleep(POLLING_INTERVAL)
        raise InstrumentationTestError('Timeout while waiting for USB '
                                       'disconnect signal.')

    def measure_power(self):
        """Measures power consumption with a power_monitor. See power_monitor's
        API for more details.

        Returns:
            A list of power_metrics.Metric.
        """
        monsoon_config = self._get_merged_config('Monsoon')
        disconnect_usb_timeout = monsoon_config.get_numeric(
            'usb_disconnection_timeout', 240)
        measurement_args = dict(
            duration=monsoon_config.get_numeric('duration'),
            hz=monsoon_config.get_numeric('frequency'),
            measure_after_seconds=monsoon_config.get_numeric('delay')
        )
        # Start measurement after receiving disconnect signal
        try:
            self._wait_for_disconnect_signal(disconnect_usb_timeout)
        except InstrumentationTestError as e:
            instrumentation_result = self.parse_instrumentation_result()
            res = self.log_instrumentation_result(instrumentation_result)
            self._reinstall_sl4a()
            raise InstrumentationTestError(
                'Failed to receive USB disconnect signal.',
                instrumentation_result=res) from e

        self.log.info('Starting measurement with options: %s' % str(
            measurement_args))

        power_data_path = os.path.join(
            context.get_current_context().get_full_output_path(), 'monsoon.txt')

        # TODO(b/155426729): Create an accurate host-to-device time difference
        # measurement.
        device_time_cmd = 'echo $EPOCHREALTIME'
        device_time = self.adb_run(device_time_cmd)[device_time_cmd]
        host_time = time.time()
        self.log.debug('device start time %s, host start time %s', device_time,
                       host_time)
        device_to_host_offset = float(device_time) - host_time

        self.power_monitor.disconnect_usb()
        self.power_monitor.measure(
            measurement_args=measurement_args, output_path=power_data_path,
            start_time=device_to_host_offset)
        self.power_monitor.connect_usb()
        self._reinstall_sl4a()

        # Gather relevant metrics from measurements
        instrumentation_result = self.parse_instrumentation_result()
        self.log_instrumentation_result(instrumentation_result)
        power_metrics = self.power_monitor.get_metrics(
            start_time=device_to_host_offset,
            voltage=monsoon_config.get_numeric('voltage', 4.2),
            monsoon_file_path=power_data_path,
            timestamps=proto_parser.get_test_timestamps(instrumentation_result))

        self.power_monitor.release_resources()
        return power_metrics

    def run_and_measure(self, instr_class, instr_method=None, req_params=None,
                        extra_params=None):
        """Convenience method for setting up the instrumentation test command,
        running it on the device, and starting the Monsoon measurement.

        Args:
            instr_class: Fully qualified name of the instrumentation test class
            instr_method: Name of the instrumentation test method
            req_params: List of required parameter names
            extra_params: List of ad-hoc parameters to be passed defined as
                tuples of size 2.

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

        if extra_params:
            for name, value in extra_params:
                self._instr_cmd_builder.add_key_value_param(name, value)

        instr_cmd = self._instr_cmd_builder.build()
        self._uninstall_sl4a()
        self.log.info('Running instrumentation call: %s' % instr_cmd)
        self.adb_run_async(instr_cmd)
        return self.measure_power()

    def get_absolute_thresholds_for_metric(self, instr_test_name, metric_name):
        all_thresholds = self._get_merged_config(ACCEPTANCE_THRESHOLD)
        test_thresholds = all_thresholds.get_config(instr_test_name)
        if metric_name not in test_thresholds:
            return None
        thresholds_conf = test_thresholds[metric_name]
        try:
            return AbsoluteThresholds.from_threshold_conf(thresholds_conf)
        except (ValueError, TypeError) as e:
            self.log.error(
                'Incorrect threshold definition for %s %s' % (instr_test_name,
                                                              metric_name))
            self.log.error('Error detail: %s', str(e))
            return None

    def record_metrics(self, power_metrics):
        """Record the collected metrics with the metric logger."""
        self.log.info('Recording metrics summaries:')
        for segment_name, metrics in power_metrics.items():
            for metric in metrics:
                self.log.info(
                    '    %s %s %s' % (segment_name, metric.name, metric))

            for metric in metrics:
                self.blackbox_logger.add_metric(
                    '%s__%s' % (metric.name, segment_name), metric.value)
                thresholds = self.get_absolute_thresholds_for_metric(
                    segment_name,
                    metric.name)

                lower_limit = None
                upper_limit = None
                if thresholds:
                    lower_limit = thresholds.lower.to_unit(metric.unit).value
                    upper_limit = thresholds.upper.to_unit(metric.unit).value

                self.bounded_metric_logger.add(
                    '%s.%s' % (segment_name, metric.name), metric.value,
                    lower_limit=lower_limit,
                    upper_limit=upper_limit,
                    unit=metric.unit)

    def validate_metrics(self, power_metrics, *instr_test_names):
        """Compare power measurements with target values and set the test result
        accordingly.

        Args:
            power_metrics: The metrics to be validated.
            instr_test_names: Name(s) of the instrumentation test method.
                If none specified, defaults to all test methods run.

        Raises:
            signals.TestFailure if one or more metrics do not satisfy threshold
        """
        summaries = {}
        failure = False
        all_thresholds = self._get_merged_config(ACCEPTANCE_THRESHOLD)

        if not instr_test_names:
            instr_test_names = all_thresholds.keys()

        for instr_test_name in instr_test_names:
            try:
                test_metrics = {metric.name: metric for metric in
                                power_metrics[instr_test_name]}
            except KeyError:
                raise InstrumentationTestError(
                    'Unable to find test method %s in instrumentation output. '
                    'Check instrumentation call results in '
                    'instrumentation_proto.txt.'
                    % instr_test_name)

            summaries[instr_test_name] = {}
            test_thresholds_configs = all_thresholds.get_config(instr_test_name)
            for metric_name, thresholds_conf in test_thresholds_configs.items():
                try:
                    actual_result = test_metrics[metric_name]
                except KeyError as e:
                    self.log.warning(
                        'Error while retrieving results for %s: %s' % (
                            metric_name, str(e)))
                    continue

                try:
                    thresholds = AbsoluteThresholds.from_threshold_conf(
                        thresholds_conf)
                except (ValueError, TypeError) as e:
                    self.log.error(
                        'Incorrect threshold definition for %s %s',
                        (instr_test_name, metric_name))
                    self.log.error('Error detail: %s', str(e))
                    continue

                summary_entry = {
                    'expected': '[%s, %s]' % (
                        thresholds.lower, thresholds.upper),
                    'actual': str(actual_result.to_unit(thresholds.unit))
                }
                summaries[instr_test_name][metric_name] = summary_entry
                if not thresholds.lower <= actual_result <= thresholds.upper:
                    failure = True
        self.log.info('Validation output: %s' % summaries)
        asserts.assert_false(
            failure,
            msg='One or more measurements do not meet the specified criteria',
            extras=summaries)
        asserts.explicit_pass(
            msg='All measurements meet the criteria',
            extras=summaries)
