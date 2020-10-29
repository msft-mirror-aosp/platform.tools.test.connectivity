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
import time

from acts import signals
from acts import utils
from acts.test_utils.power.PowerBaseTest import PowerBaseTest
from acts.test_utils.gnss import gnss_test_utils as gutils
from acts.test_utils.wifi import wifi_test_utils as wutils

DEFAULT_WAIT_TIME = 120
STANDALONE_WAIT_TIME = 1200
DPO_NV_VALUE = '15DC'
MDS_TEST_PACKAGE = 'com.google.mdstest'
MDS_RUNNER = 'com.google.mdstest.instrument.ModemConfigInstrumentation'


class PowerGTWGnssBaseTest(PowerBaseTest):
    """Power GTW Gnss Base test"""

    def setup_class(self):
        super().setup_class()
        self.ad = self.android_devices[0]
        req_params = [
            'wifi_network', 'test_location', 'qdsp6m_path',
            'calibrate_target'
        ]
        self.unpack_userparams(req_param_names=req_params)
        gutils.disable_xtra_throttle(self.ad)

    def setup_test(self):
        super().setup_test()
        # Enable GNSS setting for GNSS standalone mode
        self.ad.adb.shell('settings put secure location_mode 3')

    def teardown_test(self):
        begin_time = utils.get_current_epoch_time()
        self.ad.take_bug_report(self.test_name, begin_time)
        gutils.get_gnss_qxdm_log(self.ad, self.qdsp6m_path)

    def baseline_test(self):
        """Baseline power measurement"""
        self.ad.droid.goToSleepNow()
        self.collect_power_data()
        self.ad.log.info('TestResult AVG_Current %.2f' % self.avg_current)

    def start_gnss_tracking_with_power_data(self,
                                            mode='default',
                                            is_signal=True,
                                            freq=0,
                                            lowpower=False,
                                            meas=False):
        """Start GNSS tracking and collect power metrics.

        Args:
            is_signal: default True, False for no Gnss signal test.
            freq: an integer to set location update frequency.
            lowpower: a boolean to set GNSS Low Power Mode.
            mean: a boolean to set GNSS Measurement registeration.
        """
        self.ad.adb.shell('settings put secure location_mode 3')
        gutils.clear_aiding_data_by_gtw_gpstool(self.ad)
        gutils.start_gnss_by_gtw_gpstool(self.ad, True, 'gnss', True, freq,
                                         lowpower, meas)
        self.ad.droid.goToSleepNow()

        sv_collecting_time = DEFAULT_WAIT_TIME
        if mode == 'standalone':
            sv_collecting_time = STANDALONE_WAIT_TIME
        self.ad.log.info('Wait %d seconds for %s mode' %
                         (sv_collecting_time, mode))
        time.sleep(sv_collecting_time)

        samples = self.collect_power_data()
        self.ad.log.info('TestResult AVG_Current %.2f' % self.avg_current)
        self.calibrate_avg_current(samples)
        self.ad.send_keycode('WAKEUP')
        gutils.start_gnss_by_gtw_gpstool(self.ad, False, 'gnss')
        if is_signal:
            gutils.parse_gtw_gpstool_log(
                self.ad, self.test_location, type='gnss')

    def calibrate_avg_current(self, samples):
        """Calibrate average current by filtering AP wake up current with target
           value.

        Args:
            samples: a list of tuples where the first element is a timestamp
            and the second element is a current sample.
        """
        calibrate_results = [
            sample[1] * 1000 for sample in samples
            if sample[1] * 1000 < self.calibrate_target
        ]
        avg_current = sum(calibrate_results) / len(calibrate_results)
        self.ad.log.info('TestResult Calibrate_AVG_Current %.2f' % avg_current)

    def enable_DPO(self, enable):
        """Enable or disable the DPO option.

        Args:
            enable: True or False to enable DPO.
        """
        self.ad.log.info('Change DPO to new state: %s.' % enable)
        val = '02' if enable else '00'
        options = {'request': 'writeNV', 'item': DPO_NV_VALUE, 'data': val}
        instrument_cmd = gutils.build_instrumentation_call(
            MDS_TEST_PACKAGE, MDS_RUNNER, options=options)
        result = self.ad.adb.shell(instrument_cmd)
        if 'SUCCESS' not in result:
            self.ad.log.info(result)
            raise signals.TestFailure('DPO is not able to Turn: %s' % enable)
        self.dut_rockbottom()
