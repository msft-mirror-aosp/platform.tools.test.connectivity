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
import re
import statistics
from datetime import datetime
from acts import utils
from acts import signals
from acts.base_test import BaseTestClass
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.tel.tel_logging_utils import start_adb_tcpdump
from acts_contrib.test_utils.tel.tel_logging_utils import stop_adb_tcpdump
from acts_contrib.test_utils.tel.tel_logging_utils import get_tcpdump_log
from acts_contrib.test_utils.gnss import gnss_test_utils as gutils

CONCURRENCY_TYPE = {
    "gnss": "GNSS location received",
    "gnss_meas": "GNSS measurement received",
    "ap_location": "reportLocation"
}

GPS_XML_CONFIG = {
    "CS": [
        '    IgnorePosition=\"true\"\n', '    IgnoreEph=\"true\"\n',
        '    IgnoreTime=\"true\"\n', '    AsstIgnoreLto=\"true\"\n',
        '    IgnoreJniTime=\"true\"\n'
    ],
    "WS": [
        '    IgnorePosition=\"true\"\n', '    AsstIgnoreLto=\"true\"\n',
        '    IgnoreJniTime=\"true\"\n'
    ],
    "HS": []
}

ONCHIP_CONFIG = [
    '    EnableOnChipStopNotification=\"1\"\n',
    '    EnableOnChipStopNotification=\"2\"\n'
]


class GnssConcurrencyTest(BaseTestClass):
    """ GNSS Concurrency TTFF Tests. """

    def setup_class(self):
        super().setup_class()
        self.ad = self.android_devices[0]
        req_params = [
            "standalone_cs_criteria", "chre_tolerate_rate", "qdsp6m_path",
            "outlier_criteria", "max_outliers", "pixel_lab_location",
            "max_interval", "onchip_interval", "ttff_test_cycle"
        ]
        self.unpack_userparams(req_param_names=req_params)
        gutils._init_device(self.ad)
        self.ad.adb.shell("setprop persist.vendor.radio.adb_log_on 0")
        self.ad.adb.shell("sync")

    def setup_test(self):
        gutils.clear_logd_gnss_qxdm_log(self.ad)
        gutils.start_pixel_logger(self.ad)
        start_adb_tcpdump(self.ad)
        # related properties
        gutils.check_location_service(self.ad)
        gutils.get_baseband_and_gms_version(self.ad)
        self.load_chre_nanoapp()

    def teardown_test(self):
        gutils.stop_pixel_logger(self.ad)
        stop_adb_tcpdump(self.ad)

    def on_fail(self, test_name, begin_time):
        self.ad.take_bug_report(test_name, begin_time)
        gutils.get_gnss_qxdm_log(self.ad, self.qdsp6m_path)
        get_tcpdump_log(self.ad, test_name, begin_time)

    def is_brcm_test(self):
        """ Check the test is for BRCM and skip if not. """
        if gutils.check_chipset_vendor_by_qualcomm(self.ad):
            raise signals.TestSkip("Not BRCM chipset. Skip the test.")

    def load_chre_nanoapp(self):
        """ Load CHRE nanoapp to target Android Device. """
        for _ in range(0, 3):
            try:
                self.ad.log.info("Start to load the nanoapp")
                cmd = "chre_power_test_client load"
                if gutils.is_device_wearable(self.ad):
                    extra_cmd = "tcm /vendor/etc/chre/power_test_tcm.so"
                    cmd = " ".join([cmd, extra_cmd])
                res = self.ad.adb.shell(cmd)
                if "result 1" in res:
                    self.ad.log.info("Nano app loaded successfully")
                    break
            except Exception as e:
                self.ad.log.warning("Nano app loaded fail: %s" % e)
                gutils.reboot(self.ad)
        else:
            raise signals.TestError("Failed to load CHRE nanoapp")

    def enable_chre(self, interval_sec):
        """ Enable or disable gnss concurrency via nanoapp.

        Args:
            interval_sec: an int for frequency, set 0 as disable.
        """
        if interval_sec == 0:
            self.ad.log.info(f"Stop CHRE request")
        else:
            self.ad.log.info(
                f"Initiate CHRE with {interval_sec} seconds interval")
        interval_msec = interval_sec * 1000
        cmd = "chre_power_test_client"
        option = "enable %d" % interval_msec if interval_msec != 0 else "disable"

        for type in CONCURRENCY_TYPE.keys():
            if "ap" not in type:
                self.ad.adb.shell(" ".join([cmd, type, option]))

    def parse_concurrency_result(self,
                                 begin_time,
                                 request_type,
                                 criteria,
                                 exam_lower=True):
        """ Parse the test result with given time and criteria.

        Args:
            begin_time: test begin time.
            request_type: str for location request type.
            criteria: dictionary for test criteria.
            exam_lower: a boolean to identify the lower bond or not.
        Return: List for the failure and outlier loops and results.
        """
        results = []
        failures = []
        outliers = []
        upper_bound = criteria * (
            1 + self.chre_tolerate_rate) + self.outlier_criteria
        lower_bound = criteria * (
            1 - self.chre_tolerate_rate) - self.outlier_criteria
        search_results = self.ad.search_logcat(CONCURRENCY_TYPE[request_type],
                                               begin_time)
        if not search_results:
            raise signals.TestFailure(f"No log entry found for keyword:"
                                      f"{CONCURRENCY_TYPE[request_type]}")

        for i in range(len(search_results) - 1):
            target = search_results[i + 1]
            timedelt = target["datetime_obj"] - search_results[i]["datetime_obj"]
            timedelt_sec = timedelt.total_seconds()
            results.append(timedelt_sec)
            res_tag = ""
            if timedelt_sec > upper_bound:
                failures.append(timedelt_sec)
                res_tag = "Failure"
            elif timedelt_sec < lower_bound and exam_lower:
                failures.append(timedelt_sec)
                res_tag = "Failure"
            elif timedelt_sec > criteria * (1 + self.chre_tolerate_rate):
                outliers.append(timedelt_sec)
                res_tag = "Outlier"
            if res_tag:
                self.ad.log.error(
                    f"[{res_tag}][{target['time_stamp']}]:{timedelt_sec:.2f} sec"
                )

        res_summary = " ".join([str(res) for res in results[1:]])
        self.ad.log.info(f"[{request_type}]Overall Result: {res_summary}")
        log_prefix = f"TestResult {request_type}"
        self.ad.log.info(f"{log_prefix}_samples {len(search_results)}")
        self.ad.log.info(f"{log_prefix}_outliers {len(outliers)}")
        self.ad.log.info(f"{log_prefix}_failures {len(failures)}")
        self.ad.log.info(f"{log_prefix}_max_time {max(results):.2f}")

        return outliers, failures, results

    def run_gnss_concurrency_test(self, criteria, test_duration):
        """ Execute GNSS concurrency test steps.

        Args:
            criteria: int for test criteria.
            test_duration: int for test duration.
        """
        self.enable_chre(criteria["gnss"])
        TTFF_criteria = criteria["ap_location"] + self.standalone_cs_criteria
        gutils.process_gnss_by_gtw_gpstool(
            self.ad, TTFF_criteria, freq=criteria["ap_location"])
        self.ad.log.info("Tracking 10 sec to prevent flakiness.")
        time.sleep(10)
        begin_time = datetime.now()
        self.ad.log.info(f"Test Start at {begin_time}")
        time.sleep(test_duration)
        self.enable_chre(0)
        gutils.start_gnss_by_gtw_gpstool(self.ad, False)
        self.validate_location_test_result(begin_time, criteria)

    def run_chre_only_test(self, criteria, test_duration):
        """ Execute CHRE only test steps.

        Args:
            criteria: int for test criteria.
            test_duration: int for test duration.
        """
        begin_time = datetime.now()
        self.ad.log.info(f"Test Start at {begin_time}")
        self.enable_chre(criteria["gnss"])
        time.sleep(test_duration)
        self.enable_chre(0)
        self.validate_location_test_result(begin_time, criteria)

    def validate_location_test_result(self, begin_time, request):
        """ Validate GNSS concurrency/CHRE test results.

        Args:
            begin_time: epoc of test begin time
            request: int for test criteria.
        """
        results = {}
        outliers = {}
        failures = {}
        failure_log = ""
        for request_type, criteria in request.items():
            criteria = criteria if criteria > 1 else 1
            self.ad.log.info("Starting process %s result" % request_type)
            outliers[request_type], failures[request_type], results[
                request_type] = self.parse_concurrency_result(
                    begin_time, request_type, criteria, exam_lower=False)
            if not results[request_type]:
                failure_log += "[%s] Fail to find location report.\n" % request_type
            if len(failures[request_type]) > 0:
                failure_log += "[%s] Test exceeds criteria(%.2f): %.2f\n" % (
                    request_type, criteria, max(failures[request_type]))
            if len(outliers[request_type]) > self.max_outliers:
                failure_log += "[%s] Outliers excceds max amount: %d\n" % (
                    request_type, len(outliers[request_type]))

        if failure_log:
            raise signals.TestFailure(failure_log)

    def run_engine_switching_test(self, freq):
        """ Conduct engine switching test with given frequency.

        Args:
            freq: a list identify source1/2 frequency [freq1, freq2]
        """
        request = {"ap_location": self.max_interval}
        begin_time = datetime.now()
        self.ad.droid.startLocating(freq[0] * 1000, 0)
        time.sleep(10)
        for i in range(5):
            gutils.start_gnss_by_gtw_gpstool(self.ad, True, freq=freq[1])
            time.sleep(10)
            gutils.start_gnss_by_gtw_gpstool(self.ad, False)
        self.ad.droid.stopLocating()
        self.calculate_position_error(begin_time)
        self.validate_location_test_result(begin_time, request)

    def calculate_position_error(self, begin_time):
        """ Calculate the position error for the logcat search results.

        Args:
            begin_time: test begin time
        """
        position_errors = []
        search_results = self.ad.search_logcat("reportLocation", begin_time)
        for result in search_results:
            # search for location like 25.000717,121.455163
            regex = r"(-?\d{1,5}\.\d{1,10}),\s*(-?\d{1,5}\.\d{1,10})"
            result = re.search(regex, result["log_message"])
            if not result:
                raise ValueError("lat/lon does not found. "
                                 f"original text: {result['log_message']}")
            lat = float(result.group(1))
            lon = float(result.group(2))
            pe = gutils.calculate_position_error(lat, lon,
                                                 self.pixel_lab_location)
            position_errors.append(pe)
        self.ad.log.info("TestResult max_position_error %.2f" %
                         max(position_errors))

    def get_chre_ttff(self, interval_sec, duration):
        """ Get the TTFF for the first CHRE report.

        Args:
            interval_sec: test interval in seconds for CHRE.
            duration: test duration.
        """
        begin_time = datetime.now()
        self.ad.log.info(f"Test start at {begin_time}")
        self.enable_chre(interval_sec)
        time.sleep(duration)
        self.enable_chre(0)
        for type, pattern in CONCURRENCY_TYPE.items():
            if type == "ap_location":
                continue
            search_results = self.ad.search_logcat(pattern, begin_time)
            if not search_results:
                raise signals.TestFailure(
                    f"Unable to receive {type} report in {duration} seconds")
            else:
                ttff_stamp = search_results[0]["datetime_obj"]
                self.ad.log.info(search_results[0]["time_stamp"])
                ttff = (ttff_stamp - begin_time).total_seconds()
                self.ad.log.info(f"CHRE {type} TTFF = {ttff}")

    def add_ttff_conf(self, conf_type):
        """ Add mcu ttff config to gps.xml

        Args:
            conf_type: a string identify the config type
        """
        search_line_tag = "<gll\n"
        append_line_str = GPS_XML_CONFIG[conf_type]
        gutils.bcm_gps_xml_update_option(self.ad, "add", search_line_tag,
                                         append_line_str)

    def update_gps_conf(self, search_line, update_line):
        """ Update gps.xml content

        Args:
            search_line: target content
            update_line: update content
        """
        gutils.bcm_gps_xml_update_option(
            self.ad, "update", search_line, update_txt=update_line)

    def delete_gps_conf(self, conf_type):
        """ Delete gps.xml content

        Args:
            conf_type: a string identify the config type
        """
        search_line_tag = GPS_XML_CONFIG[conf_type]
        gutils.bcm_gps_xml_update_option(
            self.ad, "delete", delete_txt=search_line_tag)

    def preset_mcu_test(self, mode):
        """ Preseting mcu test with config and device state

        mode:
            mode: a string identify the test type
        """
        self.add_ttff_conf(mode)
        gutils.push_lhd_overlay(self.ad)
        self.ad.droid.connectivityToggleAirplaneMode(True)
        self.update_gps_conf(ONCHIP_CONFIG[1], ONCHIP_CONFIG[0])
        gutils.clear_aiding_data_by_gtw_gpstool(self.ad)
        self.ad.reboot(self.ad)
        self.load_chre_nanoapp()

    def reset_mcu_test(self, mode):
        """ Resetting mcu test with config and device state

        mode:
            mode: a string identify the test type
        """
        self.delete_gps_conf(mode)
        self.update_gps_conf(ONCHIP_CONFIG[0], ONCHIP_CONFIG[1])

    def get_mcu_ttff(self):
        """ Get mcu ttff seconds

        Return:
            ttff: a float identify ttff seconds
        """
        search_res = ""
        search_pattern = "$PGLOR,0,FIX"
        ttff_regex = r"FIX,(.*)\*"
        cmd_base = "chre_power_test_client gnss tcm"
        cmd_start = " ".join([cmd_base, "enable 1000"])
        cmd_stop = " ".join([cmd_base, "disable"])
        begin_time = datetime.now()

        self.ad.log.info("Send CHRE enable to DUT")
        self.ad.adb.shell(cmd_start)
        for i in range(6):
            search_res = self.ad.search_logcat(search_pattern, begin_time)
            if search_res:
                break
            time.sleep(10)
        else:
            self.ad.adb.shell(cmd_stop)
            self.ad.log.error("Unable to get mcu ttff in 60 seconds")
            return 60
        self.ad.adb.shell(cmd_stop)

        res = re.search(ttff_regex, search_res[0]["log_message"])
        ttff = res.group(1)
        self.ad.log.info(f"TTFF = {ttff}")
        return float(ttff)

    def run_mcu_ttff_loops(self, mode, loops):
        """ Run mcu ttff with given mode and loops

        Args:
            mode: a string identify mode cs/ws/hs.
            loops: a int to identify the number of loops
        """
        ttff_res = []
        for i in range(10):
            ttff = self.get_mcu_ttff()
            self.ad.log.info(f"{mode} TTFF LOOP{i+1} = {ttff}")
            ttff_res.append(ttff)
            time.sleep(10)
        self.ad.log.info(f"TestResult {mode}_MAX_TTFF {max(ttff_res)}")
        self.ad.log.info(
            f"TestResult {mode}_AVG_TTFF {statistics.mean(ttff_res)}")

    # Concurrency Test Cases
    @test_tracker_info(uuid="9b0daebf-461e-4005-9773-d5d10aaeaaa4")
    def test_gnss_concurrency_ct1(self):
        test_duration = 15
        criteria = {"ap_location": 1, "gnss": 1, "gnss_meas": 1}
        self.run_gnss_concurrency_test(criteria, test_duration)

    @test_tracker_info(uuid="f423db2f-12a0-4858-b66f-99e7ca6010c3")
    def test_gnss_concurrency_ct2(self):
        test_duration = 30
        criteria = {"ap_location": 1, "gnss": 8, "gnss_meas": 8}
        self.run_gnss_concurrency_test(criteria, test_duration)

    @test_tracker_info(uuid="f72d2df0-f70a-4a11-9f68-2a38f6974454")
    def test_gnss_concurrency_ct3(self):
        test_duration = 60
        criteria = {"ap_location": 15, "gnss": 8, "gnss_meas": 8}
        self.run_gnss_concurrency_test(criteria, test_duration)

    @test_tracker_info(uuid="8e5563fd-afcd-40d3-9392-7fc0d10f49da")
    def test_gnss_concurrency_aoc1(self):
        test_duration = 120
        criteria = {"ap_location": 61, "gnss": 1, "gnss_meas": 1}
        self.run_gnss_concurrency_test(criteria, test_duration)

    @test_tracker_info(uuid="fb258565-6ac8-4bf7-a554-01d63fc4ef54")
    def test_gnss_concurrency_aoc2(self):
        test_duration = 120
        criteria = {"ap_location": 61, "gnss": 10, "gnss_meas": 10}
        self.run_gnss_concurrency_test(criteria, test_duration)

    # CHRE Only Test Cases
    @test_tracker_info(uuid="cb85fa60-9f1a-4957-b5e3-0f2e5db70b47")
    def test_gnss_chre1(self):
        test_duration = 15
        criteria = {"gnss": 1, "gnss_meas": 1}
        self.run_chre_only_test(criteria, test_duration)

    @test_tracker_info(uuid="6ab17866-0d0e-4d9e-b3af-441d9db0e324")
    def test_gnss_chre2(self):
        test_duration = 30
        criteria = {"gnss": 8, "gnss_meas": 8}
        self.run_chre_only_test(criteria, test_duration)

    # Interval tests
    @test_tracker_info(uuid="53b161e5-335e-44a7-ae2e-eae7464a2b37")
    def test_variable_interval_via_chre(self):
        test_duration = 10
        intervals = [0.1, 0.5, 1.5]
        for interval in intervals:
            self.get_chre_ttff(interval, test_duration)

    @test_tracker_info(uuid="ee0a46fe-aa5f-4dfd-9cb7-d4924f9e9cea")
    def test_variable_interval_via_framework(self):
        test_duration = 10
        intervals = [0, 0.5, 1.5]
        for interval in intervals:
            begin_time = datetime.now()
            self.ad.droid.startLocating(interval * 1000, 0)
            time.sleep(test_duration)
            self.ad.droid.stopLocating()
            criteria = interval if interval > 1 else 1
            self.parse_concurrency_result(begin_time, "ap_location", criteria)

    # Engine switching test
    @test_tracker_info(uuid="8b42bcb2-cb8c-4ef9-bd98-4fb74a521224")
    def test_gps_engine_switching_host_to_onchip(self):
        self.is_brcm_test()
        freq = [1, self.onchip_interval]
        self.run_engine_switching_test(freq)

    @test_tracker_info(uuid="636041dc-2bd6-4854-aa5d-61c87943d99c")
    def test_gps_engine_switching_onchip_to_host(self):
        self.is_brcm_test()
        freq = [self.onchip_interval, 1]
        self.run_engine_switching_test(freq)

    @test_tracker_info(uuid="fd671f4a-0cc7-4894-ae5b-e9b9d470562d")
    def test_mcu_cs_ttff(self):
        mode = "CS"
        self.preset_mcu_test(mode)
        self.run_mcu_ttff_loops(mode, self.ttff_test_cycle)
        self.reset_mcu_test(mode)

    @test_tracker_info(uuid="de67334e-7538-4fc4-a8e5-bcf72a14ea82")
    def test_mcu_ws_ttff(self):
        mode = "WS"
        self.preset_mcu_test(mode)
        self.run_mcu_ttff_loops(mode, self.ttff_test_cycle)
        self.reset_mcu_test(mode)

    @test_tracker_info(uuid="c361e811-df72-4578-ab47-8cade28e79a3")
    def test_mcu_hs_ttff(self):
        mode = "HS"
        self.preset_mcu_test(mode)
        self.run_mcu_ttff_loops(mode, self.ttff_test_cycle)
        self.reset_mcu_test(mode)
