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


class Cellular5GFR2ThroughputTest(base_test.BaseTestClass):
    """Class to test cellular throughput

    This class implements cellular throughput tests on a lab/callbox setup.
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
        asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                            'Can not turn on airplane mode.')
        self.keysight_test_app.set_cell_state('LTE', 1, 0)
        self.keysight_test_app.destroy()
        self.process_testclass_results()

    def setup_test(self):
        if self.testclass_params['enable_pixel_logs']:
            cputils.start_pixel_logger(self.dut)
        self.retry_flag = False

    def on_retry(self):
        """Function to control test logic on retried tests.

        This function is automatically executed on tests that are being
        retried. In this case the function resets wifi, toggles it off and on
        and sets a retry_flag to enable further tweaking the test logic on
        second attempts.
        """
        self.retry_flag = True
        asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                            'Can not turn on airplane mode.')

    def teardown_test(self):
        self.log.info('Turing airplane mode on')
        asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                            'Can not turn on airplane mode.')
        log_path = os.path.join(
            context.get_current_context().get_full_output_path(), 'pixel_logs')
        os.makedirs(self.log_path, exist_ok=True)
        if self.testclass_params['enable_pixel_logs']:
            cputils.stop_pixel_logger(self.dut, log_path)
        self.retry_flag = False
        self.process_testcase_results()
        self.pass_fail_check()

    def process_testcase_results(self):
        if self.current_test_name in self.testclass_results:
            testcase_results = self.testclass_results[self.current_test_name]
            results_file_path = os.path.join(
                context.get_current_context().get_full_output_path(),
                '{}.json'.format(self.current_test_name))
            with open(results_file_path, 'w') as results_file:
                json.dump(wputils.serialize_dict(testcase_results),
                          results_file,
                          indent=4)

    def pass_fail_check(self):
        pass

    def process_testclass_results(self):
        """Saves CSV with all test results to enable comparison."""
        results_file_path = os.path.join(
            context.get_current_context().get_full_output_path(),
            'results.csv')
        with open(results_file_path, 'w', newline='') as csvfile:
            field_names = [
                'Band', 'DL Carriers', 'UL Carriers', 'DL MCS', 'UL MCS',
                'Cell Power', 'DL Min. Throughput', 'DL Max. Throughput',
                'DL Avg. Throughput', 'DL Theoretical Throughput',
                'UL Min. Throughput', 'UL Max. Throughput',
                'UL Avg. Throughput', 'UL Theoretical Throughput',
                'DL BLER (%)', 'UL BLER (%)', 'TCP/UDP Throughput'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            writer.writeheader()

            for testcase_name, testcase_results in self.testclass_results.items(
            ):
                for result in testcase_results['results']:
                    writer.writerow({
                        'Band':
                        testcase_results['testcase_params']['band'],
                        'DL Carriers':
                        testcase_results['testcase_params']['num_dl_cells'],
                        'UL Carriers':
                        testcase_results['testcase_params']['num_ul_cells'],
                        'DL MCS':
                        testcase_results['testcase_params']['dl_mcs'],
                        'UL MCS':
                        testcase_results['testcase_params']['ul_mcs'],
                        'Cell Power':
                        result['cell_power'],
                        'DL Min. Throughput':
                        result['tput_result']['total']['DL']['min_tput'],
                        'DL Max. Throughput':
                        result['tput_result']['total']['DL']['max_tput'],
                        'DL Avg. Throughput':
                        result['tput_result']['total']['DL']['average_tput'],
                        'DL Theoretical Throughput':
                        result['tput_result']['total']['DL']
                        ['theoretical_tput'],
                        'UL Min. Throughput':
                        result['tput_result']['total']['UL']['min_tput'],
                        'UL Max. Throughput':
                        result['tput_result']['total']['UL']['max_tput'],
                        'UL Avg. Throughput':
                        result['tput_result']['total']['UL']['average_tput'],
                        'UL Theoretical Throughput':
                        result['tput_result']['total']['UL']
                        ['theoretical_tput'],
                        'DL BLER (%)':
                        result['bler_result']['total']['DL']['nack_ratio'] *
                        100,
                        'UL BLER (%)':
                        result['bler_result']['total']['UL']['nack_ratio'] *
                        100,
                        'TCP/UDP Throughput':
                        result.get('iperf_throughput', 0)
                    })

    def test_load_scpi(self):
        """Test to load SCPI file defined in config file.

        This test loads the SCPI file referenced in the config file under
        throughput test params scpi_file parameter. It is often a useful test
        to run before other throughput tests as it sets the test application
        and callbox into a know good state.
        """
        self.keysight_test_app.import_scpi_file(
            self.testclass_params['scpi_file'])

    def setup_tester(self, testcase_params):
        if not self.keysight_test_app.get_cell_state('LTE', 'CELL1'):
            self.log.info('Turning LTE on.')
            self.keysight_test_app.set_cell_state('LTE', 'CELL1', 1)
        self.log.info('Turning off airplane mode')
        asserts.assert_true(utils.force_airplane_mode(self.dut, False),
                            'Can not turn on airplane mode.')
        self.log.info('Waiting for LTE and applying aggregation')
        for cell in testcase_params['dl_cell_list']:
            self.keysight_test_app.set_cell_band('NR5G', cell,
                                                 testcase_params['band'])
        # Consider configuring schedule quick config
        self.keysight_test_app.set_nr_cell_schedule_scenario(
            testcase_params['dl_cell_list'][0],
            testcase_params['schedule_scenario'])
        self.keysight_test_app.set_nr_ul_dft_precoding(
            testcase_params['dl_cell_list'][0],
            testcase_params['transform_precoding'])
        self.keysight_test_app.set_nr_cell_mcs(
            testcase_params['dl_cell_list'][0], testcase_params['dl_mcs'],
            testcase_params['ul_mcs'])
        self.keysight_test_app.set_dl_carriers(testcase_params['dl_cell_list'])
        self.keysight_test_app.set_ul_carriers(testcase_params['ul_cell_list'])
        self.keysight_test_app.apply_carrier_agg()
        self.log.info('Waiting for 5G connection')
        connected = self.keysight_test_app.wait_for_cell_status(
            'NR5G', testcase_params['dl_cell_list'][-1], ['ACT', 'CONN'], 60)
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
        for cell_power in testcase_params['cell_power_list']:
            result = collections.OrderedDict()
            result['cell_power'] = cell_power
            # Set DL cell power
            for cell in testcase_params['dl_cell_list']:
                self.keysight_test_app.set_cell_dl_power(
                    'NR5G', cell, result['cell_power'], 1)
            time.sleep(SHORT_SLEEP)
            # Start BLER and throughput measurements
            self.keysight_test_app.start_bler_measurement(
                'NR5G', testcase_params['dl_cell_list'],
                testcase_params['bler_measurement_length'])
            if self.testclass_params['traffic_type'] != 'PHY':
                result['iperf_throughput'] = self.run_iperf_traffic(
                    testcase_params)
            result['bler_result'] = self.keysight_test_app.get_bler_result(
                'NR5G', testcase_params['dl_cell_list'],
                testcase_params['bler_measurement_length'])
            result['tput_result'] = self.keysight_test_app.get_throughput(
                'NR5G', testcase_params['dl_cell_list'])

            # Print Test Summary
            self.log.info("Cell Power: {}dBm".format(cell_power))
            self.log.info(
                "DL PHY Tput (Mbps):\tMin: {:.2f},\tAvg: {:.2f},\tMax: {:.2f},\tTheoretical: {:.2f}"
                .format(
                    result['tput_result']['total']['DL']['min_tput'] / 1e6,
                    result['tput_result']['total']['DL']['average_tput'] / 1e6,
                    result['tput_result']['total']['DL']['max_tput'] / 1e6,
                    result['tput_result']['total']['DL']['theoretical_tput'] /
                    1e6))
            self.log.info(
                "UL PHY Tput (Mbps):\tMin: {:.2f},\tAvg: {:.2f},\tMax: {:.2f},\tTheoretical: {:.2f}"
                .format(
                    result['tput_result']['total']['UL']['min_tput'] / 1e6,
                    result['tput_result']['total']['UL']['average_tput'] / 1e6,
                    result['tput_result']['total']['UL']['max_tput'] / 1e6,
                    result['tput_result']['total']['UL']['theoretical_tput'] /
                    1e6))
            self.log.info("DL BLER: {:.2f}%\tUL BLER: {:.2f}%".format(
                result['bler_result']['total']['DL']['nack_ratio'] * 100,
                result['bler_result']['total']['UL']['nack_ratio'] * 100))
            testcase_results['results'].append(result)
            if self.testclass_params['traffic_type'] != 'PHY':
                self.log.info("{} {} Tput: {:.2f} Mbps".format(
                    self.testclass_params['traffic_type'],
                    testcase_params['traffic_direction'],
                    result['iperf_throughput']))
            #self.log.info(summary_message)
        # Turn off NR cells
        for cell in testcase_params['dl_cell_list'][::-1]:
            self.keysight_test_app.set_cell_state('NR5G', cell, 0)
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

    def generate_test_cases(self, bands, mcs_pair_list, num_dl_cells_list,
                            num_ul_cells_list, **kwargs):
        """Function that auto-generates test cases for a test class."""
        test_cases = ['test_load_scpi']

        for band, num_ul_cells, num_dl_cells, mcs_pair in itertools.product(
                bands, num_ul_cells_list, num_dl_cells_list, mcs_pair_list):
            if num_ul_cells > num_dl_cells:
                continue
            test_name = 'test_nr_throughput_bler_{}_DL_{}CC_mcs{}_UL_{}CC_mcs{}'.format(
                band, num_dl_cells, mcs_pair[0], num_ul_cells, mcs_pair[1])
            test_params = collections.OrderedDict(
                band=band,
                dl_mcs=mcs_pair[0],
                ul_mcs=mcs_pair[1],
                num_dl_cells=num_dl_cells,
                num_ul_cells=num_ul_cells,
                dl_cell_list=list(range(1, num_dl_cells + 1)),
                ul_cell_list=list(range(1, num_ul_cells + 1)),
                **kwargs)
            setattr(self, test_name,
                    partial(self._test_nr_throughput_bler, test_params))
            test_cases.append(test_name)
        return test_cases


class Cellular5GFR2_DL_ThroughputTest(Cellular5GFR2ThroughputTest):

    def __init__(self, controllers):
        super().__init__(controllers)
        self.tests = self.generate_test_cases(['N257', 'N258', 'N260', 'N261'],
                                              [(16, 4), (27, 4)],
                                              list(range(1, 9)),
                                              list(range(1, 3)),
                                              schedule_scenario="FULL_TPUT",
                                              traffic_direction='DL',
                                              transform_precoding=0)


class Cellular5GFR2_CP_UL_ThroughputTest(Cellular5GFR2ThroughputTest):

    def __init__(self, controllers):
        super().__init__(controllers)
        self.tests = self.generate_test_cases(['N257', 'N258', 'N260', 'N261'],
                                              [(4, 16), (4, 27)],
                                              list(range(1, 3)),
                                              list(range(1, 3)),
                                              schedule_scenario="UL_RMC",
                                              traffic_direction='UL',
                                              transform_precoding=0)


class Cellular5GFR2_DFTS_UL_ThroughputTest(Cellular5GFR2ThroughputTest):

    def __init__(self, controllers):
        super().__init__(controllers)
        self.tests = self.generate_test_cases(['N257', 'N258', 'N260', 'N261'],
                                              [(4, 16), (4, 27)],
                                              list(range(1, 3)),
                                              list(range(1, 3)),
                                              schedule_scenario="UL_RMC",
                                              traffic_direction='UL',
                                              transform_precoding=1)