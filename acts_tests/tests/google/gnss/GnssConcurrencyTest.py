#!/usr/bin/env python3.5
#
#   Copyright 2021 - The Android Open Source Project
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
import datetime
from acts import utils
from acts import asserts
from acts import signals
from acts.base_test import BaseTestClass
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.gnss import gnss_test_utils as gutils
from acts_contrib.test_utils.wifi import wifi_test_utils as wutils
from acts_contrib.test_utils.tel import tel_test_utils as tutils

CONCURRENCY_TYPE = {
    "gnss": "GNSS location received",
    "gnss_meas": "GNSS measurement received",
    "ap_location": "reportLocation"
}


class GnssConcurrencyTest(BaseTestClass):
    """ GNSS Concurrency TTFF Tests. """

    def setup_class(self):
        super().setup_class()
        self.ad = self.android_devices[0]
        req_params = ["standalone_cs_criteria", "tolerate_rate"]
        self.unpack_userparams(req_param_names=req_params)
        gutils._init_device(self.ad)

    def setup_test(self):
        gutils.start_pixel_logger(self.ad)
        tutils.start_adb_tcpdump(self.ad)
        # related properties
        gutils.check_location_service(self.ad)
        gutils.get_baseband_and_gms_version(self.ad)
        self.load_chre_nanoapp()

    def teardown_test(self):
        gutils.stop_pixel_logger(self.ad)
        tutils.stop_adb_tcpdump(self.ad)

    def on_fail(self, test_name, begin_time):
        self.ad.take_bug_report(test_name, begin_time)
        gutils.get_gnss_qxdm_log(self.ad, self.qdsp6m_path)
        tutils.get_tcpdump_log(self.ad, test_name, begin_time)

    def load_chre_nanoapp(self):
        """ Load CHRE nanoapp to target Android Device. """
        for _ in range(0, 3):
            try:
                self.ad.log.info("Start to load the nanoapp")
                res = self.ad.adb.shell("chre_power_test_client load")
                if "success: 1" in res:
                    self.ad.log.info("Nano app loaded successfully")
                    return "Success"
            except Exception as e:
                self.ad.log.info("Nano app loaded fail", e)
                gutils.reboot(self.ad)
        raise signals.TestError("Failed to load CHRE nanoapp")

    def enable_gnss_concurrency(self, freq):
        """ Enable or disable gnss concurrency via nanoapp.

        Args:
            freq: an int for frequency, set 0 as disable.
        """
        freq = freq * 1000
        cmd = "chre_power_test_client"
        option = "enable %d" % freq if freq != 0 else "disable"

        for type in CONCURRENCY_TYPE.keys():
            if "ap" not in type:
                self.ad.adb.shell(" ".join([cmd, type, option]))

    def run_concurrency_test(self, ap_freq, chre_freq, test_time):
        """ Run the concurrency test with specific sequence.

        Args:
            ap_freq: int for AP side location request frequency.
            chre_freq: int forCHRE side location request frequency.
            test_time: int for test duration.
        Return: test begin time.
        """
        gutils.process_gnss_by_gtw_gpstool(self.ad, self.standalone_cs_criteria)
        begin_time = utils.get_current_epoch_time()
        gutils.start_gnss_by_gtw_gpstool(self.ad, True, freq=ap_freq)
        self.enable_gnss_concurrency(chre_freq)
        time.sleep(test_time)
        self.enable_gnss_concurrency(0)
        gutils.start_gnss_by_gtw_gpstool(self.ad, False)
        return begin_time

    def parse_concurrency_result(self, begin_time, type, criteria):
        """ Parse the test result with given time and criteria.

        Args:
            begin_time: test begin time.
            type: str for location request type.
            criteria: int for test criteria.
        Return: a list for test fail loop.
        """
        result = []
        fail_loop = []
        search_results = self.ad.search_logcat(type, begin_time)
        start_time = utils.epoch_to_human_time(begin_time)
        start_time = datetime.datetime.strptime(start_time,
                                                "%m-%d-%Y %H:%M:%S ")
        result.append(
            (search_results[0]["datetime_obj"] - start_time).total_seconds())
        for i in range(len(search_results) - 1):
            timedelt = search_results[
                i + 1]["datetime_obj"] - search_results[i]["datetime_obj"]
            timedalt_sec = timedelt.total_seconds()
            result.append(timedalt_sec)
            if timedalt_sec > criteria * self.tolerate_rate:
                self.ad.log.error("Fail loop: %r" % search_results[i])
                fail_loop.append(search_results[i])
        self.ad.log.info(type, " ".join([str(res) for res in result]))
        return fail_loop

    # Test Cases
    def test_gnss_concurrency_ct1(self):
        fail_loop = {}
        criteria = {"ap_location": 1, "gnss": 1, "gnss_meas": 1}
        begin_time = self.run_concurrency_test(1, 1, 15)
        for type in CONCURRENCY_TYPE.keys():
            fail_loop[type] = self.parse_concurrency_result(
                begin_time, CONCURRENCY_TYPE[type], criteria[type])
        for type in CONCURRENCY_TYPE.keys():
            asserts.assert_true(fail_loop[type], "Failure detected")

    def test_gnss_concurrency_ct2(self):
        fail_loop = {}
        criteria = {"ap_location": 1, "gnss": 8, "gnss_meas": 8}
        begin_time = self.run_concurrency_test(1, 8, 30)
        for type in CONCURRENCY_TYPE.keys():
            fail_loop[type] = self.parse_concurrency_result(
                begin_time, CONCURRENCY_TYPE[type], criteria[type])
        for type in CONCURRENCY_TYPE.keys():
            asserts.assert_true(fail_loop[type], "Failure detected")

    def test_gnss_concurrency_ct3(self):
        fail_loop = {}
        criteria = {"ap_location": 15, "gnss": 8, "gnss_meas": 8}
        begin_time = self.run_concurrency_test(15, 8, 60)
        for type in CONCURRENCY_TYPE.keys():
            fail_loop[type] = self.parse_concurrency_result(
                begin_time, CONCURRENCY_TYPE[type], criteria[type])
        for type in CONCURRENCY_TYPE.keys():
            asserts.assert_true(fail_loop[type], "Failure detected")

    def test_gnss_concurrency_aoc1(self):
        test_results = {}
        criteria = {"ap_location": 61, "gnss": 1, "gnss_meas": 1}
        begin_time = self.run_concurrency_test(61, 1, 120)
        for type in CONCURRENCY_TYPE.keys():
            fail_loop[type] = self.parse_concurrency_result(
                begin_time, CONCURRENCY_TYPE[type], criteria[type])
        for type in CONCURRENCY_TYPE.keys():
            asserts.assert_true(fail_loop[type], "Failure detected")

    def test_gnss_concurrency_aoc2(self):
        test_results = {}
        criteria = {"ap_location": 61, "gnss": 10, "gnss_meas": 10}
        begin_time = self.run_concurrency_test(61, 10, 120)
        for type in CONCURRENCY_TYPE.keys():
            fail_loop[type] = self.parse_concurrency_result(
                begin_time, CONCURRENCY_TYPE[type], criteria[type])
        for type in CONCURRENCY_TYPE.keys():
            asserts.assert_true(fail_loop[type], "Failure detected")
