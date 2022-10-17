import time

from acts import asserts
from acts import signals
from acts.base_test import BaseTestClass
from acts.test_decorators import test_tracker_info
from acts.utils import get_current_epoch_time
from acts_contrib.test_utils.gnss import gnss_constant
from acts_contrib.test_utils.gnss import gnss_test_utils as gutils
from acts_contrib.test_utils.wifi import wifi_test_utils as wutils
from acts_contrib.test_utils.tel import tel_logging_utils
from acts_contrib.test_utils.tel.tel_test_utils import verify_internet_connection
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode


class GnssVendorFeaturesTest(BaseTestClass):
    """Validate vendor specific features."""
    def setup_class(self):
        super().setup_class()
        self.ad = self.android_devices[0]
        req_params = ["pixel_lab_network", "default_gnss_signal_attenuation", "pixel_lab_location",
                      "qdsp6m_path", "collect_logs", "ttff_test_cycle", "standalone_cs_criteria",
                      "xtra_cs_criteria",  "xtra_ws_criteria", "xtra_hs_criteria",
                      "weak_signal_xtra_cs_criteria", "weak_signal_xtra_ws_criteria",
                      "weak_signal_xtra_hs_criteria", "weak_gnss_signal_attenuation",
                      "set_attenuator"]
        self.unpack_userparams(req_param_names=req_params)
        # create hashmap for SSID
        self.ssid_map = {}
        for network in self.pixel_lab_network:
            SSID = network["SSID"]
            self.ssid_map[SSID] = network
        self.init_device()

    def init_device(self):
        """Init GNSS test devices for vendor features suite."""
        gutils._init_device(self.ad)
        gutils.disable_supl_mode(self.ad)
        gutils.enable_vendor_orbit_assistance_data(self.ad)

    def setup_test(self):
        gutils.log_current_epoch_time(self.ad, "test_start_time")
        gutils.clear_logd_gnss_qxdm_log(self.ad)
        gutils.get_baseband_and_gms_version(self.ad)
        toggle_airplane_mode(self.ad.log, self.ad, new_state=False)
        if gutils.is_wearable_btwifi(self.ad):
            wutils.wifi_toggle_state(self.ad, True)
            gutils.connect_to_wifi_network(self.ad,
                                           self.ssid_map[self.pixel_lab_network[0]["SSID"]])
        else:
            wutils.wifi_toggle_state(self.ad, False)
            gutils.set_mobile_data(self.ad, state=True)
        if not verify_internet_connection(self.ad.log, self.ad, retries=3,
                                          expected_state=True):
            raise signals.TestFailure("Fail to connect to internet.")

    def teardown_test(self):
        if self.collect_logs:
            gutils.stop_pixel_logger(self.ad)
            tel_logging_utils.stop_adb_tcpdump(self.ad)
        if self.set_attenuator:
            gutils.set_attenuator_gnss_signal(self.ad, self.attenuators,
                                              self.default_gnss_signal_attenuation)
        gutils.log_current_epoch_time(self.ad, "test_end_time")

    def on_fail(self, test_name, begin_time):
        if self.collect_logs:
            self.ad.take_bug_report(test_name, begin_time)
            gutils.get_gnss_qxdm_log(self.ad, self.qdsp6m_path)
            tel_logging_utils.get_tcpdump_log(self.ad, test_name, begin_time)

    def connect_to_wifi_with_airplane_mode_on(self):
        self.ad.log.info("Turn airplane mode on")
        toggle_airplane_mode(self.ad.log, self.ad, new_state=True)
        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

    def ttff_with_assist(self, mode, criteria):
        """Verify CS/WS TTFF functionality with Assist data.

        Args:
            mode: "csa" or "ws"
            criteria: Criteria for the test.
        """
        begin_time = get_current_epoch_time()
        gutils.process_gnss_by_gtw_gpstool(self.ad, self.standalone_cs_criteria)
        gutils.check_xtra_download(self.ad, begin_time)
        self.ad.log.info("Turn airplane mode on")
        toggle_airplane_mode(self.ad.log, self.ad, new_state=True)
        gutils.start_gnss_by_gtw_gpstool(self.ad, True)
        gutils.start_ttff_by_gtw_gpstool(self.ad, mode, iteration=self.ttff_test_cycle)
        ttff_data = gutils.process_ttff_by_gtw_gpstool(self.ad, begin_time, self.pixel_lab_location)
        result = gutils.check_ttff_data(self.ad, ttff_data, mode, criteria)
        asserts.assert_true(
            result, "TTFF %s fails to reach designated criteria of %d "
                    "seconds." % (gnss_constant.TTFF_MODE.get(mode), criteria))

    @test_tracker_info(uuid="ea3096cf-4f72-4e91-bfb3-0bcbfe865ab4")
    def test_xtra_ttff_cs_mobile_data(self):
        """Verify XTRA/LTO functionality of TTFF Cold Start with mobile data.

        Steps:
            1. TTFF Cold Start for 10 iteration.

        Expected Results:
            XTRA/LTO TTFF Cold Start results should be within xtra_cs_criteria.
        """
        gutils.run_ttff(self.ad, mode="cs", criteria=self.xtra_cs_criteria,
                        test_cycle=self.ttff_test_cycle, base_lat_long=self.pixel_lab_location,
                        collect_logs=self.collect_logs)

    @test_tracker_info(uuid="c9b22894-deb3-4dc2-af14-4dcbb8ebad66")
    def test_xtra_ttff_ws_mobile_data(self):
        """Verify XTRA/LTO functionality of TTFF Warm Start with mobile data.

        Steps:
            1. TTFF Warm Start for 10 iteration.

        Expected Results:
            XTRA/LTO TTFF Warm Start results should be within xtra_ws_criteria.
        """
        gutils.run_ttff(self.ad, mode="ws", criteria=self.xtra_ws_criteria,
                        test_cycle=self.ttff_test_cycle, base_lat_long=self.pixel_lab_location,
                        collect_logs=self.collect_logs)

    @test_tracker_info(uuid="273741e2-0815-4817-96df-9c13401119dd")
    def test_xtra_ttff_hs_mobile_data(self):
        """Verify XTRA/LTO functionality of TTFF Hot Start with mobile data.

        Steps:
            1. TTFF Hot Start for 10 iteration.

        Expected Results:
            XTRA/LTO TTFF Hot Start results should be within xtra_hs_criteria.
        """
        gutils.run_ttff(self.ad, mode="hs", criteria=self.xtra_hs_criteria,
                        test_cycle=self.ttff_test_cycle, base_lat_long=self.pixel_lab_location,
                        collect_logs=self.collect_logs)

    @test_tracker_info(uuid="c91ba740-220e-41de-81e5-43af31f63907")
    def test_xtra_ttff_cs_weak_gnss_signal(self):
        """Verify XTRA/LTO functionality of TTFF Cold Start under weak GNSS
        signal.

        Steps:
            2. Set attenuation value to weak GNSS signal.
            3. TTFF Cold Start for 10 iteration.

        Expected Results:
            XTRA/LTO TTFF Cold Start results should be within
            weak_signal_xtra_cs_criteria.
        """
        gutils.set_attenuator_gnss_signal(self.ad, self.attenuators,
                                          self.weak_gnss_signal_attenuation)
        gutils.run_ttff(self.ad, mode="cs", criteria=self.weak_signal_xtra_cs_criteria,
                        test_cycle=self.ttff_test_cycle, base_lat_long=self.pixel_lab_location,
                        collect_logs=self.collect_logs)

    @test_tracker_info(uuid="2a285be7-3571-49fb-8825-01efa2e65f10")
    def test_xtra_ttff_ws_weak_gnss_signal(self):
        """Verify XTRA/LTO functionality of TTFF Warm Start under weak GNSS
        signal.

        Steps:
            2. Set attenuation value to weak GNSS signal.
            3. TTFF Warm Start for 10 iteration.

        Expected Results:
            XTRA/LTO TTFF Warm Start results should be within
            weak_signal_xtra_ws_criteria.
        """
        gutils.set_attenuator_gnss_signal(self.ad, self.attenuators,
                                          self.weak_gnss_signal_attenuation)
        gutils.run_ttff(self.ad, mode="ws", criteria=self.weak_signal_xtra_ws_criteria,
                        test_cycle=self.ttff_test_cycle, base_lat_long=self.pixel_lab_location,
                        collect_logs=self.collect_logs)

    @test_tracker_info(uuid="249bf484-8b04-4cd9-a372-aa718e5f4ec6")
    def test_xtra_ttff_hs_weak_gnss_signal(self):
        """Verify XTRA/LTO functionality of TTFF Hot Start under weak GNSS
        signal.

        Steps:
            2. Set attenuation value to weak GNSS signal.
            3. TTFF Hot Start for 10 iteration.

        Expected Results:
            XTRA/LTO TTFF Hot Start results should be within
            weak_signal_xtra_hs_criteria.
        """
        gutils.set_attenuator_gnss_signal(self.ad, self.attenuators,
                                          self.weak_gnss_signal_attenuation)
        gutils.run_ttff(self.ad, mode="hs", criteria=self.weak_signal_xtra_hs_criteria,
                        test_cycle=self.ttff_test_cycle, base_lat_long=self.pixel_lab_location,
                        collect_logs=self.collect_logs)

    @test_tracker_info(uuid="beeb3454-bcb2-451e-83fb-26289e89b515")
    def test_xtra_ttff_cs_wifi(self):
        """Verify XTRA/LTO functionality of TTFF Cold Start with WiFi.

        Steps:
            1. Turn airplane mode on.
            2. Connect to WiFi.
            3. TTFF Cold Start for 10 iteration.

        Expected Results:
            XTRA/LTO TTFF Cold Start results should be within
            xtra_cs_criteria.
        """
        self.connect_to_wifi_with_airplane_mode_on()
        gutils.run_ttff(self.ad, mode="cs", criteria=self.xtra_cs_criteria,
                        test_cycle=self.ttff_test_cycle, base_lat_long=self.pixel_lab_location,
                        collect_logs=self.collect_logs)

    @test_tracker_info(uuid="f6e79b31-99d5-49ca-974f-4543957ea449")
    def test_xtra_ttff_ws_wifi(self):
        """Verify XTRA/LTO functionality of TTFF Warm Start with WiFi.

        Steps:
            1. Turn airplane mode on.
            2. Connect to WiFi.
            3. TTFF Warm Start for 10 iteration.

        Expected Results:
            XTRA/LTO TTFF Warm Start results should be within xtra_ws_criteria.
        """
        self.connect_to_wifi_with_airplane_mode_on()
        gutils.run_ttff(self.ad, mode="ws", criteria=self.xtra_ws_criteria,
                        test_cycle=self.ttff_test_cycle, base_lat_long=self.pixel_lab_location,
                        collect_logs=self.collect_logs)

    @test_tracker_info(uuid="8981363c-f64f-4c37-9674-46733c40473b")
    def test_xtra_ttff_hs_wifi(self):
        """Verify XTRA/LTO functionality of TTFF Hot Start with WiFi.

        Steps:
            1. Turn airplane mode on.
            2. Connect to WiFi.
            3. TTFF Hot Start for 10 iteration.

        Expected Results:
            XTRA/LTO TTFF Hot Start results should be within xtra_hs_criteria.
        """
        self.connect_to_wifi_with_airplane_mode_on()
        gutils.run_ttff(self.ad, mode="hs", criteria=self.xtra_hs_criteria,
                        test_cycle=self.ttff_test_cycle, base_lat_long=self.pixel_lab_location,
                        collect_logs=self.collect_logs)

    @test_tracker_info(uuid="1745b8a4-5925-4aa0-809a-1b17e848dc9c")
    def test_xtra_modem_ssr(self):
        """Verify XTRA/LTO functionality after modem silent reboot /
        GPS daemons restart.

        Steps:
            1. Trigger modem crash by adb/Restart GPS daemons by killing PID.
            2. Wait 1 minute for modem to recover.
            3. XTRA/LTO TTFF Cold Start for 3 iteration.
            4. Repeat Step1. to Step 3. for 5 times.

        Expected Results:
            All XTRA/LTO TTFF Cold Start results should be within
            xtra_cs_criteria.
        """
        xtra_ssr_test_result_all = []
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        for times in range(1, 6):
            begin_time = get_current_epoch_time()
            if gutils.check_chipset_vendor_by_qualcomm(self.ad):
                test_info = "XTRA after Modem SSR"
                gutils.gnss_trigger_modem_ssr_by_mds(self.ad)
            else:
                test_info = "LTO after restarting GPS daemons"
                gutils.restart_gps_daemons(self.ad)
            if not verify_internet_connection(self.ad.log, self.ad, retries=3, expected_state=True):
                raise signals.TestFailure("Fail to connect to internet.")
            gutils.process_gnss_by_gtw_gpstool(self.ad, self.standalone_cs_criteria)
            gutils.start_ttff_by_gtw_gpstool(self.ad, ttff_mode="cs", iteration=3)
            ttff_data = gutils.process_ttff_by_gtw_gpstool(self.ad, begin_time,
                                                    self.pixel_lab_location)
            xtra_ssr_test_result = gutils.check_ttff_data(
                self.ad, ttff_data, ttff_mode="Cold Start",
                criteria=self.xtra_cs_criteria)
            self.ad.log.info("%s test %d times -> %s" % (
                test_info, times, xtra_ssr_test_result))
            xtra_ssr_test_result_all.append(xtra_ssr_test_result)
        asserts.assert_true(all(xtra_ssr_test_result_all),
                            "TTFF fails to reach designated criteria")

    @test_tracker_info(uuid="4d6e81e1-3abb-4e03-b732-7b6b497a2258")
    def test_xtra_download_mobile_data(self):
        """Verify XTRA/LTO data could be downloaded via mobile data.

        Steps:
            1. Delete all GNSS aiding data.
            2. Get location fixed.
            3. Verify whether XTRA/LTO is downloaded and injected.
            4. Repeat Step 1. to Step 3. for 5 times.

        Expected Results:
            XTRA/LTO data is properly downloaded and injected via mobile data.
        """
        mobile_xtra_result_all = []
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        for i in range(1, 6):
            begin_time = get_current_epoch_time()
            gutils.process_gnss_by_gtw_gpstool(self.ad, self.standalone_cs_criteria)
            time.sleep(5)
            gutils.start_gnss_by_gtw_gpstool(self.ad, False)
            mobile_xtra_result = gutils.check_xtra_download(self.ad, begin_time)
            self.ad.log.info("Iteration %d => %s" % (i, mobile_xtra_result))
            mobile_xtra_result_all.append(mobile_xtra_result)
        asserts.assert_true(all(mobile_xtra_result_all),
                            "Fail to Download and Inject XTRA/LTO File.")

    @test_tracker_info(uuid="625ac665-1446-4406-a722-e6a19645222c")
    def test_xtra_download_wifi(self):
        """Verify XTRA/LTO data could be downloaded via WiFi.

        Steps:
            1. Connect to WiFi.
            2. Delete all GNSS aiding data.
            3. Get location fixed.
            4. Verify whether XTRA/LTO is downloaded and injected.
            5. Repeat Step 2. to Step 4. for 5 times.

        Expected Results:
            XTRA data is properly downloaded and injected via WiFi.
        """
        wifi_xtra_result_all = []
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        self.connect_to_wifi_with_airplane_mode_on()
        for i in range(1, 6):
            begin_time = get_current_epoch_time()
            gutils.process_gnss_by_gtw_gpstool(self.ad, self.standalone_cs_criteria)
            time.sleep(5)
            gutils.start_gnss_by_gtw_gpstool(self.ad, False)
            wifi_xtra_result = gutils.check_xtra_download(self.ad, begin_time)
            wifi_xtra_result_all.append(wifi_xtra_result)
            self.ad.log.info("Iteration %d => %s" % (i, wifi_xtra_result))
        asserts.assert_true(all(wifi_xtra_result_all),
                            "Fail to Download and Inject XTRA/LTO File.")

    @test_tracker_info(uuid="a9a64900-9016-46d0-ad7e-cab30e8152cd")
    def test_xtra_system_server_restart(self):
        """Verify XTRA/LTO functionality after system server restart.

        Steps:
            2. Get location fixed within xtra_cs_criteria.
            3. Restarts android runtime.
            4. Get location fixed within xtra_cs_criteria.

        Expected Results:
            Location fixed within xtra_cs_criteria.
        """
        overall_test_result = []
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        for test_loop in range(1, 6):
            gutils.process_gnss_by_gtw_gpstool(self.ad, self.xtra_cs_criteria)
            gutils.start_gnss_by_gtw_gpstool(self.ad, False)
            self.ad.restart_runtime()
            self.ad.unlock_screen(password=None)
            test_result = gutils.process_gnss_by_gtw_gpstool(self.ad, self.xtra_cs_criteria)
            gutils.start_gnss_by_gtw_gpstool(self.ad, False)
            self.ad.log.info("Iteration %d => %s" % (test_loop, test_result))
            overall_test_result.append(test_result)
        asserts.assert_true(all(overall_test_result),
                            "XTRA/LTO fail after system server restart.")

    @test_tracker_info(uuid="2c62183a-4354-4efc-92f2-84580cbd3398")
    def test_lto_download_after_reboot(self):
        """Verify LTO data could be downloaded and injected after device reboot.

        Steps:
            1. Reboot device.
            2. Verify whether LTO is auto downloaded and injected without trigger GPS.
            3. Repeat Step 1 to Step 2 for 5 times.

        Expected Results:
            LTO data is properly downloaded and injected at the first time tether to phone.
        """
        reboot_lto_test_results_all = []
        for times in range(1, 6):
            gutils.delete_lto_file(self.ad)
            gutils.reboot(self.ad)
            gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
            # Wait 20 seconds for boot busy and lto auto-download time
            time.sleep(20)
            begin_time = get_current_epoch_time()
            reboot_lto_test_result = gutils.check_xtra_download(self.ad, begin_time)
            self.ad.log.info("Iteration %d => %s" % (times, reboot_lto_test_result))
            reboot_lto_test_results_all.append(reboot_lto_test_result)
            gutils.stop_pixel_logger(self.ad)
            tel_logging_utils.stop_adb_tcpdump(self.ad)
        asserts.assert_true(all(reboot_lto_test_results_all),
                                "Fail to Download and Inject LTO File.")

    @test_tracker_info(uuid="a7048a4f-8a40-40a4-bb6c-7fc90e8227bd")
    def test_ws_with_assist(self):
        """Verify Warm Start functionality with existed LTO data.

        Steps:
            2. Make LTO is downloaded.
            3. Turn on AirPlane mode to make sure there's no network connection.
            4. TTFF Warm Start with Assist for 10 iteration.

        Expected Results:
            All TTFF Warm Start with Assist results should be within
            xtra_ws_criteria.
        """
        self.ttff_with_assist("ws", self.xtra_ws_criteria)

    @test_tracker_info(uuid="c5fb9519-63b0-42bd-bd79-fce7593604ea")
    def test_cs_with_assist(self):
        """Verify Cold Start functionality with existed LTO data.

        Steps:
            2. Make sure LTO is downloaded.
            3. Turn on AirPlane mode to make sure there's no network connection.
            4. TTFF Cold Start with Assist for 10 iteration.

        Expected Results:
            All TTFF Cold Start with Assist results should be within
            standalone_cs_criteria.
        """
        self.ttff_with_assist("csa", self.standalone_cs_criteria)
