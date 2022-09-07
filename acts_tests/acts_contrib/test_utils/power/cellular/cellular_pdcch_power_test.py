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
import os

from acts import context
import acts_contrib.test_utils.power.cellular.cellular_power_base_test as base_test


class PowerTelPDCCHTest(base_test.PowerCellularLabBaseTest):
    """ PDCCH only power test.

    In this test the UE is only listening and decoding the PDCCH channel. """

    # ODPM modem power record name
    ODPM_MODEM_RECORD_NAME = '[VSYS_PWR_MODEM]:Modem'

    # conversion unit
    S_TO_MS_FACTOR = 1000

    def __init__(self, controllers):
        super().__init__(controllers)
        self.odpm_power = None

    def power_pdcch_test(self):
        """ Measures power during PDCCH only.

        There's nothing to do here other than starting the power measurement
        and deciding for pass or fail, as the base class will handle attaching.
        Requirements for this test are that mac padding is off and that the
        inactivity timer is not enabled. """

        # Measure power
        self.collect_power_data()

        # getting ODPM modem power value
        context_path = context.get_current_context().get_full_output_path()
        self.log.debug(
            'class PowerTelPDCCHTest context path: ' + context_path
        )
        odpm_path = os.path.join(context_path, '../../odpm')
        self.log.debug('opdm path: ' + odpm_path)
        self.log.debug('ODPM list files: ')
        self.log.debug(os.listdir(odpm_path))

        elapsed_time = None
        for file in os.listdir(odpm_path):
            if 'after' in file and self.test_name in file:
                file_path = os.path.join(odpm_path, file)
                with open(file_path, 'r') as f:
                    for line in f:
                        if 'Elapsed time' in line:
                            # time elapsed in mS
                            # between 2 adb OPDM cmd
                            elapsed_time = line.split(':')[1].strip().split(' ')[0]
                            self.log.info('ODPM elapsed time: ' + elapsed_time)
                        if self.ODPM_MODEM_RECORD_NAME in line:
                            # change in cumulative enery in mWs
                            # between 2 adb OPDM cmd
                            delta_start_idx = line.index('(')
                            delta_str = line[delta_start_idx+1:-2].strip()
                            self.log.info(
                                self.ODPM_MODEM_RECORD_NAME
                                + ' delta: '
                                + delta_str
                                + ' mWs'
                            )
                            # calculate OPDM power
                            elapsed_time_s = float(elapsed_time) / self.S_TO_MS_FACTOR
                            odpm_power = float(delta_str) / elapsed_time_s
                            self.odpm_power = odpm_power
                            self.log.info(
                                'odpm power: ' + str(odpm_power) + ' mW'
                            )

        # Check if power measurement is within the required values
        self.pass_fail_check(self.avg_current)
