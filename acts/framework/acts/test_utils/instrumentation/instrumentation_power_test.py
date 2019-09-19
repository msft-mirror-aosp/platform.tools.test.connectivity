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
import time

from acts.test_utils.instrumentation import instrumentation_proto_parser \
    as proto_parser
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

from acts import context
from acts import signals

ACCEPTANCE_THRESHOLD = 'acceptance_threshold'
DISCONNECT_USB_FILE = 'disconnectusb.log'
POLLING_INTERVAL = 0.5


class InstrumentationPowerTest(InstrumentationBaseTest):
    """Instrumentation test for measuring and validating power metrics."""

    def setup_class(self):
        super().setup_class()
        self.monsoon = self.monsoons[0]
        self._setup_monsoon()

    def _prepare_device(self):
        """Prepares the device for power testing."""
        super()._prepare_device()
        self.install_power_apk()
        self.grant_permissions()

    def _cleanup_device(self):
        """Clean up device after power testing."""
        self._cleanup_test_files()

    def _setup_monsoon(self):
        """Set up the Monsoon controller for this testclass/testcase."""
        self.log.info('Setting up Monsoon %s' % self.monsoon.serial)
        monsoon_config = self._get_controller_config('Monsoon')
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
        self.log.info('Disconnecting device.')
        self.ad_dut.stop_services()
        time.sleep(1)

    def _on_reconnect(self):
        """Callback invoked by device reconnection to the Monsoon"""
        self.ad_dut.start_services()
        # Release wake lock to put device into sleep.
        self.ad_dut.droid.goToSleepNow()
        self.log.info('Device reconnected.')

    def install_power_apk(self):
        """Installs power.apk on the device."""
        power_apk_file = self._instrumentation_config.get_file('power_apk')
        self.ad_apps.install(power_apk_file, '-g')
        if not self.ad_apps.is_installed(power_apk_file):
            raise InstrumentationTestError('Failed to install power test APK.')
        self._power_test_pkg = self.ad_apps.get_package_name(power_apk_file)

    def _cleanup_test_files(self):
        """Remove test-generated files from the device."""
        for file_name in [DISCONNECT_USB_FILE, DEFAULT_INST_LOG_DIR,
                          DEFAULT_NOHUP_LOG]:
            path = os.path.join(
                self.ad_dut.adb.shell('echo $EXTERNAL_STORAGE'), file_name)
            self.adb_run('rm -rf %s' % path)

    # Test runtime utils

    @property
    def power_instrumentation_command_builder(self):
        """Return the default command builder for power tests"""
        builder = InstrumentationTestCommandBuilder.default()
        builder.set_manifest_package(self._power_test_pkg)
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
        self.monsoon.usb('auto')
        measure_start_time = time.time()
        result = self.monsoon.measure_power(
            **self._measurement_args, output_path=power_data_path)
        self.monsoon.usb('on')

        # Gather relevant metrics from measurements
        session = self.dump_instrumentation_result_proto()
        self._power_metrics = PowerMetrics(self._monsoon_voltage,
                                           start_time=measure_start_time)
        self._power_metrics.generate_test_metrics(
            PowerMetrics.import_raw_data(power_data_path),
            proto_parser.get_test_timestamps(session))
        return result

    def validate_power_results(self, instr_test_name):
        """Compare power measurements with target values and set the test result
        accordingly.

        Args:
            instr_test_name: Name of the instrumentation test method

        Raises:
            signals.TestFailure if one or more metrics do not satisfy threshold
            signals.TestPass otherwise
        """
        acceptance_thresholds = self._instrumentation_config \
            .get_config(self.__class__.__name__) \
            .get_config(self.current_test_name) \
            .get_config(ACCEPTANCE_THRESHOLD)
        failures = {}
        try:
            test_metrics = self._power_metrics.test_metrics[instr_test_name]
        except KeyError:
            raise InstrumentationTestError(
                'Unable to find test method %s in instrumentation output.'
                % instr_test_name)

        for metric_name, metric in acceptance_thresholds.items():
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
                failures[metric_name] = {
                    'expected': '[%s, %s]' % (lower_bound, upper_bound),
                    'actual': str(actual_result)
                }
        if failures:
            raise signals.TestFailure('One or more measurements does not meet '
                                      'the specified criteria', failures)
        raise signals.TestPass('All measurements meet the specified criteria',
                               test_metrics.summary)
