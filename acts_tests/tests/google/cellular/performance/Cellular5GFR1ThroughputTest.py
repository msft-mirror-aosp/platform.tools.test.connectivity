#!/usr/bin/env python3.4
#
#   Copyright 2022 - The Android Open Source Project
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

import collections
import csv
import itertools
import json
import re

import numpy
import os
import time
from acts import asserts
from acts import context
from acts import base_test
from acts import utils
from acts.metrics.loggers.blackbox import BlackboxMappedMetricLogger
from acts.controllers.utils_lib import ssh
from acts.controllers import iperf_server as ipf
from acts_contrib.test_utils.cellular.keysight_5g_testapp import Keysight5GTestApp
from acts_contrib.test_utils.cellular import cellular_performance_test_utils as cputils
from acts_contrib.test_utils.wifi import wifi_performance_test_utils as wputils

from functools import partial

LONG_SLEEP = 10
MEDIUM_SLEEP = 2
IPERF_TIMEOUT = 10
SHORT_SLEEP = 1
SUBFRAME_LENGTH = 0.001
STOP_COUNTER_LIMIT = 3


class Cellular5GFR1ThroughputTest(base_test.BaseTestClass):
    """Class to test cellular 5G FR1 throughput

    This class implements cellular 5G FR1 throughput tests on a lab/callbox setup.
    The class setups up the callbox in the desired configurations, configures
    and connects the phone, and runs traffic/iperf throughput.
    """

    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.testcase_metric_logger = (
            BlackboxMappedMetricLogger.for_test_case())
        self.testclass_metric_logger = (
            BlackboxMappedMetricLogger.for_test_class())
        self.publish_testcase_metrics = True

    def setup_class(self):
        """Initializes common test hardware and parameters.

        This function initializes hardwares and compiles parameters that are
        common to all tests in this class.
        """
        self.dut = self.android_devices[-1]
        self.testclass_params = self.user_params['throughput_test_params']
        self.keysight_test_app = Keysight5GTestApp(
            self.user_params['Keysight5GTestApp'])
        self.testclass_results = collections.OrderedDict()
        self.iperf_server = self.iperf_servers[0]
        self.iperf_client = self.iperf_clients[0]
        self.remote_server = ssh.connection.SshConnection(
            ssh.settings.from_config(
                self.user_params['RemoteServer']['ssh_config']))
        if self.testclass_params.get('reload_scpi', 1):
            self.keysight_test_app.import_scpi_file(
                self.testclass_params['scpi_file'])
        # Configure test retries
        self.user_params['retry_tests'] = [self.__class__.__name__]

        # Turn Airplane mode on
        asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                            'Can not turn on airplane mode.')

    def teardown_class(self):
        self.log.info('Turning airplane mode on')
        try:
            asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                                'Can not turn on airplane mode.')
        except:
            self.log.warning('Cannot perform teardown operations on DUT.')
        try:
            self.keysight_test_app.set_cell_state('LTE', 1, 0)
            self.keysight_test_app.destroy()
        except:
            self.log.warning('Cannot perform teardown operations on tester.')
        self.process_testclass_results()

    def setup_test(self):
        if self.testclass_params['enable_pixel_logs']:
            cputils.start_pixel_logger(self.dut)

    def on_retry(self):
        """Function to control test logic on retried tests.

        This function is automatically executed on tests that are being
        retried. In this case the function resets wifi, toggles it off and on
        and sets a retry_flag to enable further tweaking the test logic on
        second attempts.
        """
        asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                            'Can not turn on airplane mode.')
        if self.keysight_test_app.get_cell_state('LTE', 'CELL1'):
            self.log.info('Turning LTE off.')
            self.keysight_test_app.set_cell_state('LTE', 'CELL1', 0)

    def teardown_test(self):
        self.log.info('Turing airplane mode on')
        asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                            'Can not turn on airplane mode.')
        if self.keysight_test_app.get_cell_state('LTE', 'CELL1'):
            self.log.info('Turning LTE off.')
            self.keysight_test_app.set_cell_state('LTE', 'CELL1', 0)
        log_path = os.path.join(
            context.get_current_context().get_full_output_path(), 'pixel_logs')
        os.makedirs(self.log_path, exist_ok=True)
        if self.testclass_params['enable_pixel_logs']:
            cputils.stop_pixel_logger(self.dut, log_path)
        self.process_testcase_results()
        self.pass_fail_check()

    def process_testcase_results(self):
        pass
        if self.current_test_name not in self.testclass_results:
            return
        testcase_data = self.testclass_results[self.current_test_name]
        results_file_path = os.path.join(
            context.get_current_context().get_full_output_path(),
            '{}.json'.format(self.current_test_name))
        with open(results_file_path, 'w') as results_file:
            json.dump(wputils.serialize_dict(testcase_data),
                      results_file,
                      indent=4)
        testcase_result = testcase_data['results'][0]
        metric_map = {
            'tcp_udp_tput': testcase_result.get('iperf_throughput',
                                                float('nan'))
        }
        if testcase_data['testcase_params']['endc_combo_config'][
                'nr_cell_count']:
            metric_map.update({
                'nr_min_dl_tput':
                testcase_result['nr_tput_result']['total']['DL']['min_tput'],
                'nr_max_dl_tput':
                testcase_result['nr_tput_result']['total']['DL']['max_tput'],
                'nr_avg_dl_tput':
                testcase_result['nr_tput_result']['total']['DL']
                ['average_tput'],
                'nr_theoretical_dl_tput':
                testcase_result['nr_tput_result']['total']['DL']
                ['theoretical_tput'],
                'nr_dl_bler':
                testcase_result['nr_bler_result']['total']['DL']['nack_ratio']
                * 100,
                'nr_min_dl_tput':
                testcase_result['nr_tput_result']['total']['UL']['min_tput'],
                'nr_max_dl_tput':
                testcase_result['nr_tput_result']['total']['UL']['max_tput'],
                'nr_avg_dl_tput':
                testcase_result['nr_tput_result']['total']['UL']
                ['average_tput'],
                'nr_theoretical_dl_tput':
                testcase_result['nr_tput_result']['total']['UL']
                ['theoretical_tput'],
                'nr_ul_bler':
                testcase_result['nr_bler_result']['total']['UL']['nack_ratio']
                * 100
            })
        if testcase_data['testcase_params']['endc_combo_config'][
                'lte_cell_count']:
            metric_map.update({
                'lte_min_dl_tput':
                testcase_result['lte_tput_result']['total']['DL']['min_tput'],
                'lte_max_dl_tput':
                testcase_result['lte_tput_result']['total']['DL']['max_tput'],
                'lte_avg_dl_tput':
                testcase_result['lte_tput_result']['total']['DL']
                ['average_tput'],
                'lte_theoretical_dl_tput':
                testcase_result['lte_tput_result']['total']['DL']
                ['theoretical_tput'],
                'lte_dl_bler':
                testcase_result['lte_bler_result']['total']['DL']['nack_ratio']
                * 100,
                'lte_min_dl_tput':
                testcase_result['lte_tput_result']['total']['UL']['min_tput'],
                'lte_max_dl_tput':
                testcase_result['lte_tput_result']['total']['UL']['max_tput'],
                'lte_avg_dl_tput':
                testcase_result['lte_tput_result']['total']['UL']
                ['average_tput'],
                'lte_theoretical_dl_tput':
                testcase_result['lte_tput_result']['total']['UL']
                ['theoretical_tput'],
                'lte_ul_bler':
                testcase_result['lte_bler_result']['total']['UL']['nack_ratio']
                * 100
            })
        if self.publish_testcase_metrics:
            for metric_name, metric_value in metric_map.items():
                self.testcase_metric_logger.add_metric(metric_name,
                                                       metric_value)

    def pass_fail_check(self):
        pass

    def process_testclass_results(self):
        """Saves CSV with all test results to enable comparison."""
        results_file_path = os.path.join(
            context.get_current_context().get_full_output_path(),
            'results.csv')
        with open(results_file_path, 'w', newline='') as csvfile:
            field_names = [
                'Test Name', 'NR DL Min. Throughput', 'NR DL Max. Throughput',
                'NR DL Avg. Throughput', 'NR DL Theoretical Throughput',
                'NR UL Min. Throughput', 'NR UL Max. Throughput',
                'NR UL Avg. Throughput', 'NR UL Theoretical Throughput',
                'NR DL BLER (%)', 'NR UL BLER (%)', 'LTE DL Min. Throughput',
                'LTE DL Max. Throughput', 'LTE DL Avg. Throughput',
                'LTE DL Theoretical Throughput', 'LTE UL Min. Throughput',
                'LTE UL Max. Throughput', 'LTE UL Avg. Throughput',
                'LTE UL Theoretical Throughput', 'LTE DL BLER (%)',
                'LTE UL BLER (%)', 'TCP/UDP Throughput'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            writer.writeheader()

            for testcase_name, testcase_results in self.testclass_results.items(
            ):
                for result in testcase_results['results']:
                    row_dict = {
                        'Test Name': testcase_name,
                        'TCP/UDP Throughput':
                        result.get('iperf_throughput', 0)
                    }
                    if testcase_results['testcase_params'][
                            'endc_combo_config']['nr_cell_count']:
                        row_dict.update({
                            'NR DL Min. Throughput':
                            result['nr_tput_result']['total']['DL']
                            ['min_tput'],
                            'NR DL Max. Throughput':
                            result['nr_tput_result']['total']['DL']
                            ['max_tput'],
                            'NR DL Avg. Throughput':
                            result['nr_tput_result']['total']['DL']
                            ['average_tput'],
                            'NR DL Theoretical Throughput':
                            result['nr_tput_result']['total']['DL']
                            ['theoretical_tput'],
                            'NR UL Min. Throughput':
                            result['nr_tput_result']['total']['UL']
                            ['min_tput'],
                            'NR UL Max. Throughput':
                            result['nr_tput_result']['total']['UL']
                            ['max_tput'],
                            'NR UL Avg. Throughput':
                            result['nr_tput_result']['total']['UL']
                            ['average_tput'],
                            'NR UL Theoretical Throughput':
                            result['nr_tput_result']['total']['UL']
                            ['theoretical_tput'],
                            'NR DL BLER (%)':
                            result['nr_bler_result']['total']['DL']
                            ['nack_ratio'] * 100,
                            'NR UL BLER (%)':
                            result['nr_bler_result']['total']['UL']
                            ['nack_ratio'] * 100
                        })
                    if testcase_results['testcase_params'][
                            'endc_combo_config']['lte_cell_count']:
                        row_dict.update({
                            'LTE DL Min. Throughput':
                            result['lte_tput_result']['total']['DL']
                            ['min_tput'],
                            'LTE DL Max. Throughput':
                            result['lte_tput_result']['total']['DL']
                            ['max_tput'],
                            'LTE DL Avg. Throughput':
                            result['lte_tput_result']['total']['DL']
                            ['average_tput'],
                            'LTE DL Theoretical Throughput':
                            result['lte_tput_result']['total']['DL']
                            ['theoretical_tput'],
                            'LTE UL Min. Throughput':
                            result['lte_tput_result']['total']['UL']
                            ['min_tput'],
                            'LTE UL Max. Throughput':
                            result['lte_tput_result']['total']['UL']
                            ['max_tput'],
                            'LTE UL Avg. Throughput':
                            result['lte_tput_result']['total']['UL']
                            ['average_tput'],
                            'LTE UL Theoretical Throughput':
                            result['lte_tput_result']['total']['UL']
                            ['theoretical_tput'],
                            'LTE DL BLER (%)':
                            result['lte_bler_result']['total']['DL']
                            ['nack_ratio'] * 100,
                            'LTE UL BLER (%)':
                            result['lte_bler_result']['total']['UL']
                            ['nack_ratio'] * 100
                        })
                    writer.writerow(row_dict)

    def setup_tester(self, testcase_params):
        # Configure all cells
        for cell in testcase_params['endc_combo_config']['cell_list']:
            self.keysight_test_app.set_cell_duplex_mode(
                cell['cell_type'], cell['cell_number'], cell['duplex_mode'])
            self.keysight_test_app.set_cell_band(cell['cell_type'],
                                                 cell['cell_number'],
                                                 cell['band'])
            if cell['cell_type'] == 'NR5G':
                self.keysight_test_app.set_nr_subcarrier_spacing(
                    cell['cell_number'], cell['subcarrier_spacing'])
            if cell.get('channel', False):
                self.keysight_test_app.set_cell_channel(
                    cell['cell_type'], cell['cell_number'], cell['channel'])
            self.keysight_test_app.set_cell_bandwidth(cell['cell_type'],
                                                      cell['cell_number'],
                                                      cell['dl_bandwidth'])
            self.keysight_test_app.set_cell_mimo_config(
                cell['cell_type'], cell['cell_number'], 'DL',
                cell['dl_mimo_config'])
            if cell['ul_enabled'] and cell['cell_type'] == 'NR5G':
                self.keysight_test_app.set_cell_mimo_config(
                    cell['cell_type'], cell['cell_number'], 'UL',
                    cell['ul_mimo_config'])

        if testcase_params['endc_combo_config']['lte_cell_count']:
            self.keysight_test_app.set_lte_cell_mcs(
                'CELL1', testcase_params['lte_dl_mcs_table'],
                testcase_params['lte_dl_mcs'],
                testcase_params['lte_ul_mcs_table'],
                testcase_params['lte_ul_mcs'])
            self.keysight_test_app.set_lte_ul_mac_padding(1)

        # Turn on LTE cells
        for cell in testcase_params['endc_combo_config']['cell_list']:
            if cell['cell_type'] == 'LTE' and not self.keysight_test_app.get_cell_state(
                    cell['cell_type'], cell['cell_number']):
                self.log.info('Turning LTE Cell {} on.'.format(
                    cell['cell_number']))
                self.keysight_test_app.set_cell_state(cell['cell_type'],
                                                      cell['cell_number'], 1)

        # Activate LTE aggregation
        if testcase_params['endc_combo_config']['lte_scc_list']:
            self.keysight_test_app.apply_lte_carrier_agg(
                testcase_params['endc_combo_config']['lte_scc_list'])

        if testcase_params['endc_combo_config']['nr_cell_count']:
            # self.keysight_test_app.set_nr_cell_schedule_scenario(
            #     'CELL1',
            #     testcase_params['schedule_scenario'])
            self.keysight_test_app.set_nr_ul_dft_precoding(
                'CELL1', testcase_params['transform_precoding'])
            self.keysight_test_app.set_nr_cell_mcs(
                'CELL1', testcase_params['nr_dl_mcs'],
                testcase_params['nr_ul_mcs'])
            self.keysight_test_app.set_dl_carriers(
                testcase_params['endc_combo_config']['nr_dl_carriers'])
            self.keysight_test_app.set_ul_carriers(
                testcase_params['endc_combo_config']['nr_ul_carriers'])

        self.log.info('Waiting for LTE connections')
        # Turn airplane mode off
        num_apm_toggles = 5
        for idx in range(num_apm_toggles):
            self.log.info('Turning off airplane mode')
            asserts.assert_true(utils.force_airplane_mode(self.dut, False),
                                'Can not turn off airplane mode.')
            if self.keysight_test_app.wait_for_cell_status(
                    'LTE', 'CELL1', 'CONN', 180):
                break
            elif idx < num_apm_toggles - 1:
                self.log.info('Turning on airplane mode')
                asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                                    'Can not turn on airplane mode.')
                time.sleep(MEDIUM_SLEEP)
            else:
                asserts.fail('DUT did not connect to LTE.')

        if testcase_params['endc_combo_config']['nr_cell_count']:
            self.keysight_test_app.apply_carrier_agg()
            self.log.info('Waiting for 5G connection')
            connected = self.keysight_test_app.wait_for_cell_status(
                'NR5G', testcase_params['endc_combo_config']['nr_cell_count'],
                ['ACT', 'CONN'], 60)
            if not connected:
                asserts.fail('DUT did not connect to NR.')
        time.sleep(SHORT_SLEEP)

    def run_iperf_traffic(self, testcase_params):
        self.iperf_server.start(tag=0)
        dut_ip = self.dut.droid.connectivityGetIPv4Addresses('rmnet0')[0]
        if 'iperf_server_address' in self.testclass_params:
            iperf_server_address = self.testclass_params[
                'iperf_server_address']
        elif isinstance(self.iperf_server, ipf.IPerfServerOverAdb):
            iperf_server_address = dut_ip
        else:
            iperf_server_address = wputils.get_server_address(
                self.remote_server, dut_ip, '255.255.255.0')
        client_output_path = self.iperf_client.start(
            iperf_server_address, testcase_params['iperf_args'], 0,
            self.testclass_params['traffic_duration'] + IPERF_TIMEOUT)
        server_output_path = self.iperf_server.stop()
        # Parse and log result
        if testcase_params['use_client_output']:
            iperf_file = client_output_path
        else:
            iperf_file = server_output_path
        try:
            iperf_result = ipf.IPerfResult(iperf_file)
            current_throughput = numpy.mean(iperf_result.instantaneous_rates[
                self.testclass_params['iperf_ignored_interval']:-1]) * 8 * (
                    1.024**2)
        except:
            self.log.warning(
                'ValueError: Cannot get iperf result. Setting to 0')
            current_throughput = 0
        return current_throughput

    def _test_nr_throughput_bler(self, testcase_params):
        """Test function to run cellular throughput and BLER measurements.

        The function runs BLER/throughput measurement after configuring the
        callbox and DUT. The test supports running PHY or TCP/UDP layer traffic
        in a variety of band/carrier/mcs/etc configurations.

        Args:
            testcase_params: dict containing test-specific parameters
        Returns:
            result: dict containing throughput results and meta data
        """
        testcase_params = self.compile_test_params(testcase_params)
        testcase_results = collections.OrderedDict()
        testcase_results['testcase_params'] = testcase_params
        testcase_results['results'] = []
        # Setup tester and wait for DUT to connect
        self.setup_tester(testcase_params)
        # Run test
        stop_counter = 0
        for cell_power in testcase_params['cell_power_list']:
            result = collections.OrderedDict()
            result['cell_power'] = cell_power
            # Set DL cell power
            for cell in testcase_params['endc_combo_config']['cell_list']:
                self.keysight_test_app.set_cell_dl_power(
                    cell['cell_type'], cell['cell_number'],
                    result['cell_power'], 1)
            #self.keysight_test_app.select_display_tab(
            #   'NR5G', cell['cell_number'], 'BTHR', 'OTAGRAPH')

            # Start BLER and throughput measurements
            self.log.info('Starting BLER & throughput tests.')
            if testcase_params['endc_combo_config']['nr_cell_count']:
                self.keysight_test_app.start_bler_measurement(
                    'NR5G',
                    testcase_params['endc_combo_config']['nr_dl_carriers'],
                    testcase_params['bler_measurement_length'])
            if testcase_params['endc_combo_config']['lte_cell_count']:
                self.keysight_test_app.start_bler_measurement(
                    'LTE',
                    testcase_params['endc_combo_config']['lte_carriers'][0],
                    testcase_params['bler_measurement_length'])

            if self.testclass_params['traffic_type'] != 'PHY':
                result['iperf_throughput'] = self.run_iperf_traffic(
                    testcase_params)

            if testcase_params['endc_combo_config']['nr_cell_count']:
                result[
                    'nr_bler_result'] = self.keysight_test_app.get_bler_result(
                        'NR5G',
                        testcase_params['endc_combo_config']['nr_dl_carriers'],
                        testcase_params['bler_measurement_length'])
                result[
                    'nr_tput_result'] = self.keysight_test_app.get_throughput(
                        'NR5G',
                        testcase_params['endc_combo_config']['nr_dl_carriers'])
            if testcase_params['endc_combo_config']['lte_cell_count']:
                result[
                    'lte_bler_result'] = self.keysight_test_app.get_bler_result(
                        'LTE',
                        testcase_params['endc_combo_config']['lte_carriers'],
                        testcase_params['bler_measurement_length'])
                result[
                    'lte_tput_result'] = self.keysight_test_app.get_throughput(
                        'LTE',
                        testcase_params['endc_combo_config']['lte_carriers'])
            # Print Test Summary
            self.log.info("Cell Power: {}dBm".format(cell_power))
            if testcase_params['endc_combo_config']['nr_cell_count']:
                self.log.info(
                    "----NR5G STATS-------NR5G STATS-------NR5G STATS---")
                self.log.info(
                    "DL PHY Tput (Mbps):\tMin: {:.2f},\tAvg: {:.2f},\tMax: {:.2f},\tTheoretical: {:.2f}"
                    .format(
                        result['nr_tput_result']['total']['DL']['min_tput'] /
                        1e6,
                        result['nr_tput_result']['total']['DL']['average_tput']
                        / 1e6,
                        result['nr_tput_result']['total']['DL']['max_tput'] /
                        1e6, result['nr_tput_result']['total']['DL']
                        ['theoretical_tput'] / 1e6))
                self.log.info(
                    "UL PHY Tput (Mbps):\tMin: {:.2f},\tAvg: {:.2f},\tMax: {:.2f},\tTheoretical: {:.2f}"
                    .format(
                        result['nr_tput_result']['total']['UL']['min_tput'] /
                        1e6,
                        result['nr_tput_result']['total']['UL']['average_tput']
                        / 1e6,
                        result['nr_tput_result']['total']['UL']['max_tput'] /
                        1e6, result['nr_tput_result']['total']['UL']
                        ['theoretical_tput'] / 1e6))
                self.log.info("DL BLER: {:.2f}%\tUL BLER: {:.2f}%".format(
                    result['nr_bler_result']['total']['DL']['nack_ratio'] *
                    100,
                    result['nr_bler_result']['total']['UL']['nack_ratio'] *
                    100))
            if testcase_params['endc_combo_config']['lte_cell_count']:
                self.log.info(
                    "----LTE STATS-------LTE STATS-------LTE STATS---")
                self.log.info(
                    "DL PHY Tput (Mbps):\tMin: {:.2f},\tAvg: {:.2f},\tMax: {:.2f},\tTheoretical: {:.2f}"
                    .format(
                        result['lte_tput_result']['total']['DL']['min_tput'] /
                        1e6, result['lte_tput_result']['total']['DL']
                        ['average_tput'] / 1e6,
                        result['lte_tput_result']['total']['DL']['max_tput'] /
                        1e6, result['lte_tput_result']['total']['DL']
                        ['theoretical_tput'] / 1e6))
                self.log.info(
                    "UL PHY Tput (Mbps):\tMin: {:.2f},\tAvg: {:.2f},\tMax: {:.2f},\tTheoretical: {:.2f}"
                    .format(
                        result['lte_tput_result']['total']['UL']['min_tput'] /
                        1e6, result['lte_tput_result']['total']['UL']
                        ['average_tput'] / 1e6,
                        result['lte_tput_result']['total']['UL']['max_tput'] /
                        1e6, result['lte_tput_result']['total']['UL']
                        ['theoretical_tput'] / 1e6))
                self.log.info("DL BLER: {:.2f}%\tUL BLER: {:.2f}%".format(
                    result['lte_bler_result']['total']['DL']['nack_ratio'] *
                    100,
                    result['lte_bler_result']['total']['UL']['nack_ratio'] *
                    100))

            testcase_results['results'].append(result)
            if self.testclass_params['traffic_type'] != 'PHY':
                self.log.info("{} {} Tput: {:.2f} Mbps".format(
                    self.testclass_params['traffic_type'],
                    testcase_params['traffic_direction'],
                    result['iperf_throughput']))

            # if result['nr_bler_result']['total']['DL']['nack_ratio'] * 100 > 99:
            #     stop_counter = stop_counter + 1
            # else:
            #     stop_counter = 0
            # if stop_counter == STOP_COUNTER_LIMIT:
            #     break
        # Turn off NR cells
        self.keysight_test_app.set_cell_state('LTE', 1, 0)
        asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                            'Can not turn on airplane mode.')

        # Save results
        self.testclass_results[self.current_test_name] = testcase_results

    def compile_test_params(self, testcase_params):
        """Function that completes all test params based on the test name.

        Args:
            testcase_params: dict containing test-specific parameters
        """
        testcase_params['bler_measurement_length'] = int(
            self.testclass_params['traffic_duration'] / SUBFRAME_LENGTH)
        testcase_params['cell_power_list'] = numpy.arange(
            self.testclass_params['cell_power_start'],
            self.testclass_params['cell_power_stop'],
            self.testclass_params['cell_power_step'])
        if self.testclass_params['traffic_type'] == 'PHY':
            return testcase_params
        if self.testclass_params['traffic_type'] == 'TCP':
            testcase_params['iperf_socket_size'] = self.testclass_params.get(
                'tcp_socket_size', None)
            testcase_params['iperf_processes'] = self.testclass_params.get(
                'tcp_processes', 1)
        elif self.testclass_params['traffic_type'] == 'UDP':
            testcase_params['iperf_socket_size'] = self.testclass_params.get(
                'udp_socket_size', None)
            testcase_params['iperf_processes'] = self.testclass_params.get(
                'udp_processes', 1)
        if (testcase_params['traffic_direction'] == 'DL'
                and not isinstance(self.iperf_server, ipf.IPerfServerOverAdb)
            ) or (testcase_params['traffic_direction'] == 'UL'
                  and isinstance(self.iperf_server, ipf.IPerfServerOverAdb)):
            testcase_params['iperf_args'] = wputils.get_iperf_arg_string(
                duration=self.testclass_params['traffic_duration'],
                reverse_direction=1,
                traffic_type=self.testclass_params['traffic_type'],
                socket_size=testcase_params['iperf_socket_size'],
                num_processes=testcase_params['iperf_processes'],
                udp_throughput=self.testclass_params['UDP_rates'].get(
                    testcase_params['num_dl_cells'],
                    self.testclass_params['UDP_rates']["default"]),
                udp_length=1440)
            testcase_params['use_client_output'] = True
        elif (testcase_params['traffic_direction'] == 'UL'
              and not isinstance(self.iperf_server, ipf.IPerfServerOverAdb)
              ) or (testcase_params['traffic_direction'] == 'DL'
                    and isinstance(self.iperf_server, ipf.IPerfServerOverAdb)):
            testcase_params['iperf_args'] = wputils.get_iperf_arg_string(
                duration=self.testclass_params['traffic_duration'],
                reverse_direction=0,
                traffic_type=self.testclass_params['traffic_type'],
                socket_size=testcase_params['iperf_socket_size'],
                num_processes=testcase_params['iperf_processes'],
                udp_throughput=self.testclass_params['UDP_rates'].get(
                    testcase_params['num_dl_cells'],
                    self.testclass_params['UDP_rates']["default"]),
                udp_length=1440)
            testcase_params['use_client_output'] = False
        return testcase_params


class Cellular_LTE_FR1_ENDC_ThroughputTest(Cellular5GFR1ThroughputTest):

    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.testcase_metric_logger = (
            BlackboxMappedMetricLogger.for_test_case())
        self.testclass_metric_logger = (
            BlackboxMappedMetricLogger.for_test_class())
        self.publish_testcase_metrics = True
        self.tests = self.generate_test_cases([(27, 4), (4, 27)],
                                              lte_dl_mcs_table='ASUBframes',
                                              lte_ul_mcs_table='QAM64',
                                              schedule_scenario='FULL_TPUT',
                                              transform_precoding=0)

    def generate_endc_combo_config(self, endc_combo_str):
        endc_combo_str = endc_combo_str.replace(' ', '')
        endc_combo_list = endc_combo_str.split('+')
        endc_combo_list = [combo.split(';') for combo in endc_combo_list]
        endc_combo_config = collections.OrderedDict()
        cell_config_list = list()
        lte_cell_count = 0
        nr_cell_count = 0
        lte_scc_list = []
        nr_dl_carriers = []
        nr_ul_carriers = []
        lte_carriers = []

        for cell in endc_combo_list:
            cell_config = {}
            dl_config_str = cell[0]
            dl_config_regex = re.compile(
                r'(?P<cell_type>[B,N])(?P<band>[0-9]+)(?P<bandwidth_class>[A-Z])\[(?P<mimo_config>[0-9])\]'
            )
            dl_config_match = re.match(dl_config_regex, dl_config_str)
            if dl_config_match.group('cell_type') == 'B':
                cell_config['cell_type'] = 'LTE'
                lte_cell_count = lte_cell_count + 1
                cell_config['cell_number'] = lte_cell_count
                if cell_config['cell_number'] == 1:
                    cell_config['pcc'] = 1
                    endc_combo_config['lte_pcc'] = cell_config['cell_number']
                else:
                    cell_config['pcc'] = 0
                    lte_scc_list.append(cell_config['cell_number'])
                cell_config['band'] = dl_config_match.group('band')
                cell_config['duplex_mode'] = 'FDD' if int(
                    cell_config['band']
                ) in cputils.DUPLEX_MODE_TO_BAND_MAPPING['LTE'][
                    'FDD'] else 'TDD'
                cell_config['dl_mimo_config'] = 'D{nss}U{nss}'.format(
                    nss=dl_config_match.group('mimo_config'))
                lte_carriers.append(cell_config['cell_number'])
            else:
                cell_config['cell_type'] = 'NR5G'
                nr_cell_count = nr_cell_count + 1
                cell_config['cell_number'] = nr_cell_count
                nr_dl_carriers.append(cell_config['cell_number'])
                cell_config['band'] = 'N' + dl_config_match.group('band')
                cell_config['duplex_mode'] = 'FDD' if cell_config[
                    'band'] in cputils.DUPLEX_MODE_TO_BAND_MAPPING['NR5G'][
                        'FDD'] else 'TDD'
                cell_config['subcarrier_spacing'] = 'MU0' if cell_config[
                    'duplex_mode'] == 'FDD' else 'MU1'
                cell_config['dl_mimo_config'] = 'N{nss}X{nss}'.format(
                    nss=dl_config_match.group('mimo_config'))

            cell_config['dl_bandwidth_class'] = dl_config_match.group(
                'bandwidth_class')
            cell_config['dl_bandwidth'] = 'BW20'
            cell_config['ul_enabled'] = len(cell) > 1
            if cell_config['ul_enabled']:
                ul_config_str = cell[1]
                ul_config_regex = re.compile(
                    r'(?P<bandwidth_class>[A-Z])\[(?P<mimo_config>[0-9])\]')
                ul_config_match = re.match(ul_config_regex, ul_config_str)
                cell_config['ul_bandwidth_class'] = ul_config_match.group(
                    'bandwidth_class')
                cell_config['ul_mimo_config'] = 'N{nss}X{nss}'.format(
                    nss=ul_config_match.group('mimo_config'))
                if cell_config['cell_type'] == 'NR5G':
                    nr_ul_carriers.append(cell_config['cell_number'])
            cell_config_list.append(cell_config)
        endc_combo_config['lte_cell_count'] = lte_cell_count
        endc_combo_config['nr_cell_count'] = nr_cell_count
        endc_combo_config['nr_dl_carriers'] = nr_dl_carriers
        endc_combo_config['nr_ul_carriers'] = nr_ul_carriers
        endc_combo_config['cell_list'] = cell_config_list
        endc_combo_config['lte_scc_list'] = lte_scc_list
        endc_combo_config['lte_carriers'] = lte_carriers
        return endc_combo_config

    def generate_test_cases(self, mcs_pair_list, **kwargs):
        test_cases = []

        with open(
                self.user_params['throughput_test_params']['endc_combo_file'],
                'r') as endc_combos:
            for endc_combo_str in endc_combos:
                if endc_combo_str[0] == '#':
                    continue
                endc_combo_config = self.generate_endc_combo_config(
                    endc_combo_str)
                special_chars = '+[];\n'
                for char in special_chars:
                    endc_combo_str = endc_combo_str.replace(char, '_')
                endc_combo_str = endc_combo_str.replace('__', '_')
                endc_combo_str = endc_combo_str.strip('_')
                for mcs_pair in mcs_pair_list:
                    test_name = 'test_lte_fr1_endc_{}_dl_mcs{}_ul_mcs{}'.format(
                        endc_combo_str, mcs_pair[0], mcs_pair[1])
                    test_params = collections.OrderedDict(
                        endc_combo_config=endc_combo_config,
                        nr_dl_mcs=mcs_pair[0],
                        nr_ul_mcs=mcs_pair[1],
                        lte_dl_mcs=mcs_pair[0],
                        lte_ul_mcs=mcs_pair[1],
                        **kwargs)
                    setattr(
                        self, test_name,
                        partial(self._test_nr_throughput_bler, test_params))
                    test_cases.append(test_name)
        return test_cases


class Cellular_SingleCell_ThroughputTest(Cellular5GFR1ThroughputTest):

    def generate_endc_combo_config(self, test_config):
        endc_combo_config = collections.OrderedDict()
        lte_cell_count = 0
        nr_cell_count = 0
        lte_scc_list = []
        nr_dl_carriers = []
        nr_ul_carriers = []
        lte_carriers = []

        cell_config_list = []
        if test_config['lte_band']:
            lte_cell = {
                'cell_type':
                'LTE',
                'cell_number':
                1,
                'pcc':
                1,
                'band':
                test_config['lte_band'],
                'dl_bandwidth':
                test_config['lte_bandwidth'],
                'ul_enabled':
                1,
                'duplex_mode':
                test_config['lte_duplex_mode'],
                'dl_mimo_config':
                'D{nss}U{nss}'.format(nss=test_config['lte_dl_mimo_config']),
                'ul_mimo_config':
                'D{nss}U{nss}'.format(nss=test_config['lte_ul_mimo_config'])
            }
            cell_config_list.append(lte_cell)
            endc_combo_config['lte_pcc'] = 1
            lte_cell_count = 1
            lte_carriers = [1]

        if test_config['nr_band']:
            nr_cell = {
                'cell_type':
                'NR5G',
                'cell_number':
                1,
                'band':
                test_config['nr_band'],
                'duplex_mode':
                test_config['nr_duplex_mode'],
                'dl_mimo_config':
                'N{nss}X{nss}'.format(nss=test_config['nr_dl_mimo_config']),
                'dl_bandwidth_class':
                'A',
                'dl_bandwidth':
                test_config['nr_bandwidth'],
                'ul_enabled':
                1,
                'ul_bandwidth_class':
                'A',
                'ul_mimo_config':
                'N{nss}X{nss}'.format(nss=test_config['nr_ul_mimo_config']),
                'subcarrier_spacing':
                'MU0' if test_config['nr_scs'] == '15' else 'MU1'
            }
            cell_config_list.append(nr_cell)
            nr_cell_count = 1
            nr_dl_carriers = [1]
            nr_ul_carriers = [1]

        endc_combo_config['lte_cell_count'] = lte_cell_count
        endc_combo_config['nr_cell_count'] = nr_cell_count
        endc_combo_config['nr_dl_carriers'] = nr_dl_carriers
        endc_combo_config['nr_ul_carriers'] = nr_ul_carriers
        endc_combo_config['cell_list'] = cell_config_list
        endc_combo_config['lte_scc_list'] = lte_scc_list
        endc_combo_config['lte_carriers'] = lte_carriers
        return endc_combo_config


class Cellular_FR1_SingleCell_ThroughputTest(Cellular_SingleCell_ThroughputTest
                                             ):

    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.testcase_metric_logger = (
            BlackboxMappedMetricLogger.for_test_case())
        self.testclass_metric_logger = (
            BlackboxMappedMetricLogger.for_test_class())
        self.publish_testcase_metrics = True
        self.tests = self.generate_test_cases(
            nr_mcs_pair_list=[(27, 4), (4, 27)],
            channel_list=['LOW', 'MID', 'HIGH'],
            schedule_scenario='FULL_TPUT',
            transform_precoding=0,
            lte_dl_mcs=4,
            lte_dl_mcs_table='ASUBframes',
            lte_ul_mcs=4,
            lte_ul_mcs_table='QAM64')

    def generate_test_cases(self, nr_mcs_pair_list, channel_list, **kwargs):

        test_cases = []
        with open(
                self.user_params['throughput_test_params']
            ['nr_single_cell_configs'], 'r') as csvfile:
            test_configs = csv.DictReader(csvfile)
            for test_config, channel, nr_mcs_pair in itertools.product(
                    test_configs, channel_list, nr_mcs_pair_list):
                if int(test_config['skip_test']):
                    continue
                endc_combo_config = self.generate_endc_combo_config(
                    test_config)
                endc_combo_config['cell_list'][1]['channel'] = channel
                test_name = 'test_fr1_{}_{}_dl_mcs{}_ul_mcs{}'.format(
                    test_config['nr_band'], channel.lower(), nr_mcs_pair[0],
                    nr_mcs_pair[1])
                test_params = collections.OrderedDict(
                    endc_combo_config=endc_combo_config,
                    nr_dl_mcs=nr_mcs_pair[0],
                    nr_ul_mcs=nr_mcs_pair[1],
                    **kwargs)
                setattr(self, test_name,
                        partial(self._test_nr_throughput_bler, test_params))
                test_cases.append(test_name)
        return test_cases


class Cellular_LTE_SingleCell_ThroughputTest(Cellular_SingleCell_ThroughputTest
                                             ):

    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.testcase_metric_logger = (
            BlackboxMappedMetricLogger.for_test_case())
        self.testclass_metric_logger = (
            BlackboxMappedMetricLogger.for_test_class())
        self.publish_testcase_metrics = True
        self.tests = self.generate_test_cases(lte_mcs_pair_list=[
            (('ASUBframes', 27), ('QAM256', 4)),
            (('ASUBframes', 4), ('QAM256', 27))
        ],
                                              schedule_scenario='FULL_TPUT',
                                              transform_precoding=0)

    def generate_test_cases(self, lte_mcs_pair_list, **kwargs):
        test_cases = []
        with open(
                self.user_params['throughput_test_params']
            ['lte_single_cell_configs'], 'r') as csvfile:
            test_configs = csv.DictReader(csvfile)
            for test_config, lte_mcs_pair in itertools.product(
                    test_configs, lte_mcs_pair_list):
                if int(test_config['skip_test']):
                    continue
                endc_combo_config = self.generate_endc_combo_config(
                    test_config)
                test_name = 'test_lte_B{}_dl_mcs{}_ul_mcs{}'.format(
                    test_config['lte_band'], lte_mcs_pair[0], lte_mcs_pair[1])
                test_params = collections.OrderedDict(
                    endc_combo_config=endc_combo_config,
                    lte_dl_mcs_table=lte_mcs_pair[0][0],
                    lte_dl_mcs=lte_mcs_pair[0][1],
                    lte_ul_mcs_table=lte_mcs_pair[1][0],
                    lte_ul_mcs=lte_mcs_pair[1][1],
                    **kwargs)
                setattr(self, test_name,
                        partial(self._test_nr_throughput_bler, test_params))
                test_cases.append(test_name)
        return test_cases
