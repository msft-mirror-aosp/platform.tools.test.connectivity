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
from acts_contrib.test_utils.cellular.keysight_5g_testapp import Keysight5GTestApp
from acts_contrib.test_utils.cellular import cellular_performance_test_utils as cputils
from acts_contrib.test_utils.wifi import wifi_performance_test_utils as wputils
from functools import partial


class CellularRxPowerTest(base_test.BaseTestClass):
    """Class to test cellular throughput."""

    def __init__(self, controllers):
        base_test.BaseTestClass.__init__(self, controllers)
        self.testcase_metric_logger = (
            BlackboxMappedMetricLogger.for_test_case())
        self.testclass_metric_logger = (
            BlackboxMappedMetricLogger.for_test_class())
        self.publish_testcase_metrics = True
        self.tests = self.generate_test_cases(['N257', 'N258', 'N260', 'N261'],
                                              list(range(1, 9)))

    def setup_class(self):
        """Initializes common test hardware and parameters.

        This function initializes hardwares and compiles parameters that are
        common to all tests in this class.
        """
        self.dut = self.android_devices[-1]
        self.testclass_params = self.user_params['rx_power_params']
        self.keysight_test_app = Keysight5GTestApp(
            self.user_params['Keysight5GTestApp'])
        self.testclass_results = []
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

    def setup_test(self):
        cputils.start_pixel_logger(self.dut)

    def teardown_test(self):
        self.log.info('Turning airplane mode on')
        asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                            'Can not turn on airplane mode.')
        log_path = os.path.join(
            context.get_current_context().get_full_output_path(), 'pixel_logs')
        os.makedirs(self.log_path, exist_ok=True)
        cputils.stop_pixel_logger(self.dut, log_path)

    def _test_nr_rsrp(self, testcase_params):
        """Test function to run cellular RSRP tests.

        The function runs a sweep of cell powers while collecting pixel logs
        for later postprocessing and RSRP analysis.

        Args:
            testcase_params: dict containing test-specific parameters
        """

        result = collections.OrderedDict()
        testcase_params['power_range_vector'] = list(
            numpy.arange(self.testclass_params['cell_power_start'],
                         self.testclass_params['cell_power_stop'],
                         self.testclass_params['cell_power_step']))

        if not self.keysight_test_app.get_cell_state('LTE', 'CELL1'):
            self.log.info('Turning LTE on.')
            self.keysight_test_app.set_cell_state('LTE', 'CELL1', 1)
        self.log.info('Turning off airplane mode')
        asserts.assert_true(utils.force_airplane_mode(self.dut, False),
                            'Can not turn on airplane mode.')
        self.log.info('Waiting for LTE and applying aggregation')
        for cell in testcase_params['cell_list']:
            self.keysight_test_app.set_cell_band('NR5G', cell,
                                                 testcase_params['band'])
        # Consider configuring schedule quick config
        self.keysight_test_app.set_nr_cell_schedule_scenario(
            testcase_params['cell_list'][0], 'BASIC')
        self.keysight_test_app.set_dl_carriers(testcase_params['cell_list'])
        self.keysight_test_app.set_ul_carriers(testcase_params['cell_list'][0])
        self.keysight_test_app.apply_carrier_agg()
        self.log.info('Waiting for 5G connection')
        connected = self.keysight_test_app.wait_for_cell_status(
            'NR5G', testcase_params['cell_list'][-1], ['ACT', 'CONN'], 60)
        if not connected:
            asserts.fail('DUT did not connect to NR.')
        for cell_power in testcase_params['power_range_vector']:
            self.log.info('Setting power to {} dBm'.format(cell_power))
            for cell in testcase_params['cell_list']:
                self.keysight_test_app.set_cell_dl_power(
                    'NR5G', cell, True, cell_power)
            time.sleep(5)

        for cell in testcase_params['cell_list'][::-1]:
            self.keysight_test_app.set_cell_state('NR5G', cell, 0)
        asserts.assert_true(utils.force_airplane_mode(self.dut, True),
                            'Can not turn on airplane mode.')
        # Save results
        result['testcase_params'] = testcase_params
        self.testclass_results.append(result)
        results_file_path = os.path.join(
            context.get_current_context().get_full_output_path(),
            '{}.json'.format(self.current_test_name))
        with open(results_file_path, 'w') as results_file:
            json.dump(wputils.serialize_dict(result), results_file, indent=4)

    def generate_test_cases(self, bands, num_cells_list):
        """Function that auto-generates test cases for a test class."""
        test_cases = []

        for band, num_cells in itertools.product(bands, num_cells_list):
            test_name = 'test_nr_rsrp_{}_{}CC'.format(band, num_cells)
            test_params = collections.OrderedDict(band=band,
                                                  num_cells=num_cells,
                                                  cell_list=list(
                                                      range(1, num_cells + 1)))
            setattr(self, test_name, partial(self._test_nr_rsrp, test_params))
            test_cases.append(test_name)
        return test_cases