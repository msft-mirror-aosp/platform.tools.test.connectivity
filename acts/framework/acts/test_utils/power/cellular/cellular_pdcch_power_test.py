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

import acts.test_utils.power.cellular.cellular_power_base_test as base_test


class PowerTelPDCCHTest(base_test.PowerCellularLabBaseTest):
    """ PDCCH only power test.

    In this test the UE is only listening and decoding the PDCCH channel. """
    def power_pdcch_test(self):
        """ Measures power during PDCCH only.

        There's nothing to do here other than starting the power measurement
        and deciding for pass or fail, as the base class will handle attaching.
        Requirements for this test are that mac padding is off and that the
        inactivity timer is not enabled. """

        # Measure power
        result = self.collect_power_data()

        # Check if power measurement is within the required values
        self.pass_fail_check(result.average_current)
