#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
#
##   Licensed under the Apache License, Version 2.0 (the 'License');
##   you may not use this file except in compliance with the License.
##   You may obtain a copy of the License at
##
##       http://www.apache.org/licenses/LICENSE-2.0
##
##   Unless required by applicable law or agreed to in writing, software
##   distributed under the License is distributed on an 'AS IS' BASIS,
##   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##   See the License for the specific language governing permissions and
##   limitations under the License.

from acts_contrib.test_utils.gnss import LabTtffTestBase as lttb
from acts_contrib.test_utils.gnss.gnss_test_utils import launch_eecoexer
from acts_contrib.test_utils.gnss.gnss_test_utils import excute_eecoexer_function


class LabTtffCellCoexTest(lttb.LabTtffTestBase):
    """Lab stand alone GNSS cellular coex TTFF/FFPE test"""

    def setup_class(self):
        super().setup_class()
        req_params = ['cell_testcase_ls']
        self.unpack_userparams(req_param_names=req_params)

    def setup_test(self):
        super().setup_test()
        launch_eecoexer(self.dut)
        # Set DUT temperature the limit to 60 degree
        self.dut.adb.shell(
            'setprop persist.com.google.eecoexer.cellular.temperature_limit 60')

    def gnss_ttff_ffpe_cell_coex_base(self, mode):
        """
        TTFF and FFPE cellular coex base test function

            Args:
                mode: Set the TTFF mode for testing. Definitions are as below.
                cs(cold start), ws(warm start), hs(hot start)
        """
        # EEcoexer cellular stop Tx command
        stop_cell_tx_cmd = 'CELLR,19'

        # Test loop for all cellular test cases in cell_testcase_ls.
        for test_item in self.cell_testcase_ls:
            # Create the log path for each test case in cell_testcase_ls
            test_log_path = test_item.replace(',', '_')

            # Start cellular Tx by EEcoexer
            self.log.info('Start EEcoexer Test Command: {}'.format(test_item))
            excute_eecoexer_function(self.dut, test_item)

            # Start GNSS TTFF FFPE testing
            self.gnss_ttff_ffpe(mode, test_log_path)

            # Stop cellular Tx by EEcoexer
            self.log.info(
                'Stop EEcoexer Test Command: {}'.format(stop_cell_tx_cmd))
            excute_eecoexer_function(self.dut, stop_cell_tx_cmd)

            # Clear GTW GPSTool log. Need to clean the log every round of the test.
            self.clear_gps_log()

    def test_gnss_cold_ttff_ffpe_cell_coex(self):
        """
        Cold start TTFF and FFPE cellular coex testing
        """
        self.gnss_ttff_ffpe_cell_coex_base('cs')

    def test_gnss_warm_ttff_ffpe_cell_coex(self):
        """
        Warm start TTFF and FFPE cellular coex testing
        """
        self.gnss_ttff_ffpe_cell_coex_base('ws')

    def test_gnss_hot_ttff_ffpe_cell_coex(self):
        """
        Hot start TTFF and FFPE cellular coex testing
        """
        self.gnss_ttff_ffpe_cell_coex_base('hs')
