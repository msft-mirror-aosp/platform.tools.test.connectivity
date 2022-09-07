from multiprocessing import Process
import time

from acts import asserts
from acts import signals
from acts.base_test import BaseTestClass
from acts.test_decorators import test_tracker_info
from acts.utils import get_current_epoch_time
from acts_contrib.test_utils.gnss import gnss_test_utils as gutils
from acts_contrib.test_utils.gnss import supl
from acts_contrib.test_utils.tel.tel_data_utils import http_file_download_by_sl4a
from acts_contrib.test_utils.tel.tel_logging_utils import get_tcpdump_log
from acts_contrib.test_utils.tel.tel_logging_utils import stop_adb_tcpdump
from acts_contrib.test_utils.tel.tel_logging_utils import get_tcpdump_log
from acts_contrib.test_utils.tel.tel_test_utils import check_call_state_connected_by_adb
from acts_contrib.test_utils.tel.tel_test_utils import verify_internet_connection
from acts_contrib.test_utils.tel.tel_voice_utils import initiate_call
from acts_contrib.test_utils.wifi import wifi_test_utils as wutils


class GnssSuplTest(BaseTestClass):
    def setup_class(self):
        super().setup_class()
        self.ad = self.android_devices[0]
        req_params = [
            "pixel_lab_network", "standalone_cs_criteria", "supl_cs_criteria", "supl_ws_criteria",
            "supl_hs_criteria", "weak_signal_supl_cs_criteria", "weak_signal_supl_ws_criteria",
            "weak_signal_supl_hs_criteria", "default_gnss_signal_attenuation", "pixel_lab_location",
            "qdsp6m_path", "collect_logs", "ttff_test_cycle", "project_limit_lte",
            "project_limit_lte_btwifi", "weak_gnss_signal_attenuation", "supl_capabilities",
            "no_gnss_signal_attenuation", "set_attenuator"
        ]
        self.unpack_userparams(req_param_names=req_params)
        # create hashmap for SSID
        self.ssid_map = {}
        for network in self.pixel_lab_network:
            SSID = network["SSID"]
            self.ssid_map[SSID] = network
        self.init_device()

    def runs_on_projects(self, projects):
        """Check test case should be executed on specific projects
        Args:
            phone_projects: (list) list of project name,
                default value: [] -> runs on all projects
        """
        if projects and self.ad.model not in projects:
            raise signals.TestSkip("Not expected project, skip the test. Runs on %s, got: %s" %
                                   (projects, self.ad.model))

    def init_device(self):
        """Init GNSS test devices for SUPL suite."""
        gutils.enable_gnss_verbose_logging(self.ad)
        gutils.prepare_gps_overlay(self.ad)
        gutils.enable_supl_mode(self.ad)
        gutils.set_screen_always_on(self.ad)
        gutils.check_location_service(self.ad)
        gutils.disable_private_dns_mode(self.ad)
        gutils.init_gtw_gpstool(self.ad)
        gutils.disable_vendor_orbit_assistance_data(self.ad)
        self.enable_supl_over_wifi()
        gutils.reboot(self.ad)

    def enable_supl_over_wifi(self):
        try:
            self.runs_on_projects(self.project_limit_lte_btwifi)
            supl.set_supl_over_wifi_state(self.ad, turn_on=True)
        except signals.TestSkip:
            self.ad.log.info("Skip enabling supl over wifi due to project not supported")

    def setup_test(self):
        gutils.clear_logd_gnss_qxdm_log(self.ad)
        gutils.get_baseband_and_gms_version(self.ad)
        self.ad.droid.connectivityToggleAirplaneMode(False)
        if gutils.is_wearable_btwifi(self.ad):
            wutils.wifi_toggle_state(self.ad, True)
            gutils.connect_to_wifi_network(self.ad,
                                           self.ssid_map[self.pixel_lab_network[0]["SSID"]])
        else:
            wutils.wifi_toggle_state(self.ad, False)
            gutils.set_mobile_data(self.ad, state=True)
        if not verify_internet_connection(self.ad.log, self.ad, retries=3,
                                          expected_state=True):
            raise signals.TestFailure("Fail to connect to LTE network.")
        # Once the device is rebooted, the xtra service will be alive again
        # In order not to affect the supl case, disable it in setup_test.
        if gutils.check_chipset_vendor_by_qualcomm(self.ad):
            gutils.disable_qualcomm_orbit_assistance_data(self.ad)

    def teardown_test(self):
        if self.collect_logs:
            gutils.stop_pixel_logger(self.ad)
            stop_adb_tcpdump(self.ad)
        if self.set_attenuator:
            gutils.set_attenuator_gnss_signal(self.ad, self.attenuators,
                                              self.default_gnss_signal_attenuation)

    def on_fail(self, test_name, begin_time):
        if self.collect_logs:
            self.ad.take_bug_report(test_name, begin_time)
            gutils.get_gnss_qxdm_log(self.ad, self.qdsp6m_path)
            get_tcpdump_log(self.ad, test_name, begin_time)

    def run_ttff(self, mode, criteria):
        """Triggers TTFF.

        Args:
            mode: "cs", "ws" or "hs"
            criteria: Criteria for the test.
        """
        gutils.run_ttff(self.ad, mode, criteria, self.ttff_test_cycle, self.pixel_lab_location,
                        self.collect_logs)

    def supl_ttff_weak_gnss_signal(self, mode, criteria):
        """Verify SUPL TTFF functionality under weak GNSS signal.

        Args:
            mode: "cs", "ws" or "hs"
            criteria: Criteria for the test.
        """
        gutils.set_attenuator_gnss_signal(self.ad, self.attenuators,
                                          self.weak_gnss_signal_attenuation)
        self.run_ttff(mode, criteria)

    def connect_to_wifi_with_mobile_data_off(self):
        gutils.set_mobile_data(self.ad, False)
        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

    def connect_to_wifi_with_airplane_mode_on(self):
        self.ad.droid.connectivityToggleAirplaneMode(True)
        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

    @test_tracker_info(uuid="ff318483-411c-411a-8b1a-422bd54f4a3f")
    def test_supl_capabilities(self):
        """Verify SUPL capabilities.

        Steps:
            1. Root DUT.
            2. Check SUPL capabilities.

        Expected Results:
            CAPABILITIES=0x37 which supports MSA + MSB.
            CAPABILITIES=0x17 = ON_DEMAND_TIME | MSA | MSB | SCHEDULING
        """
        if not gutils.check_chipset_vendor_by_qualcomm(self.ad):
            raise signals.TestSkip("Not Qualcomm chipset. Skip the test.")
        capabilities_state = str(
            self.ad.adb.shell(
                "cat vendor/etc/gps.conf | grep CAPABILITIES")).split("=")[-1]
        self.ad.log.info("SUPL capabilities - %s" % capabilities_state)

        asserts.assert_true(capabilities_state in self.supl_capabilities,
                            "Wrong default SUPL capabilities is set. Found %s, "
                            "expected any of %r" % (capabilities_state,
                                                    self.supl_capabilities))


    @test_tracker_info(uuid="a59c72af-5d56-4d88-9746-ae2749cac671")
    def test_supl_ttff_cs(self):
        """Verify SUPL functionality of TTFF Cold Start.

        Steps:
            1. Kill XTRA/LTO daemon to support SUPL only case.
            2. SUPL TTFF Cold Start for 10 iteration.

        Expected Results:
            All SUPL TTFF Cold Start results should be less than
            supl_cs_criteria.
        """
        self.run_ttff("cs", self.supl_cs_criteria)

    @test_tracker_info(uuid="9a91c8ad-1978-414a-a9ac-8ebc782f77ff")
    def test_supl_ttff_ws(self):
        """Verify SUPL functionality of TTFF Warm Start.

        Steps:
            1. Kill XTRA/LTO daemon to support SUPL only case.
            2. SUPL TTFF Warm Start for 10 iteration.

        Expected Results:
            All SUPL TTFF Warm Start results should be less than
            supl_ws_criteria.
        """
        self.run_ttff("ws", self.supl_ws_criteria)

    @test_tracker_info(uuid="bbd5aad4-3309-4579-a3b2-a06bfb674dfa")
    def test_supl_ttff_hs(self):
        """Verify SUPL functionality of TTFF Hot Start.

        Steps:
            1. Kill XTRA/LTO daemon to support SUPL only case.
            2. SUPL TTFF Hot Start for 10 iteration.

        Expected Results:
            All SUPL TTFF Hot Start results should be less than
            supl_hs_criteria.
        """
        self.run_ttff("hs", self.supl_hs_criteria)

    @test_tracker_info(uuid="60c0aeec-0c8f-4a96-bc6c-05cba1260e73")
    def test_supl_ongoing_call(self):
        """Verify SUPL functionality during phone call.

        Steps:
            1. Kill XTRA/LTO daemon to support SUPL only case.
            2. Initiate call on DUT.
            3. SUPL TTFF Cold Start for 10 iteration.
            4. DUT hang up call.

        Expected Results:
            All SUPL TTFF Cold Start results should be less than
            supl_cs_criteria.
        """
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        self.ad.droid.setVoiceCallVolume(25)
        initiate_call(self.ad.log, self.ad, "99117")
        time.sleep(5)
        if not check_call_state_connected_by_adb(self.ad):
            raise signals.TestFailure("Call is not connected.")
        self.run_ttff("cs", self.supl_cs_criteria)

    @test_tracker_info(uuid="df605509-328f-43e8-b6d8-00635bf701ef")
    def test_supl_downloading_files(self):
        """Verify SUPL functionality when downloading files.

        Steps:
            1. Kill XTRA/LTO daemon to support SUPL only case.
            2. DUT start downloading files by sl4a.
            3. SUPL TTFF Cold Start for 10 iteration.
            4. DUT cancel downloading files.

        Expected Results:
            All SUPL TTFF Cold Start results should be within supl_cs_criteria.
        """
        begin_time = get_current_epoch_time()
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        download = Process(target=http_file_download_by_sl4a,
                           args=(self.ad, "https://speed.hetzner.de/10GB.bin",
                                 None, None, True, 3600))
        download.start()
        time.sleep(10)
        gutils.process_gnss_by_gtw_gpstool(self.ad, self.standalone_cs_criteria)
        gutils.start_ttff_by_gtw_gpstool(
            self.ad, ttff_mode="cs", iteration=self.ttff_test_cycle)
        ttff_data = gutils.process_ttff_by_gtw_gpstool(self.ad, begin_time, self.pixel_lab_location)
        download.terminate()
        time.sleep(3)
        result = gutils.check_ttff_data(self.ad, ttff_data, ttff_mode="Cold Start",
                                        criteria=self.supl_cs_criteria)

        asserts.assert_true(result, "TTFF fails to reach designated criteria")

    @test_tracker_info(uuid="66b9f9d4-1397-4da7-9e55-8b89b1732017")
    def test_supl_watching_youtube(self):
        """Verify SUPL functionality when watching video on youtube.

        Steps:
            1. Kill XTRA/LTO daemon to support SUPL only case.
            2. DUT start watching video on youtube.
            3. SUPL TTFF Cold Start for 10 iteration at the background.
            4. DUT stop watching video on youtube.

        Expected Results:
            All SUPL TTFF Cold Start results should be within supl_cs_criteria.
        """
        begin_time = get_current_epoch_time()
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        self.ad.droid.setMediaVolume(25)
        gutils.process_gnss_by_gtw_gpstool(self.ad, self.standalone_cs_criteria)
        gutils.start_ttff_by_gtw_gpstool(
            self.ad, ttff_mode="cs", iteration=self.ttff_test_cycle)
        gutils.start_youtube_video(self.ad,
                                   url="https://www.youtube.com/watch?v=AbdVsi1VjQY",
                                   retries=3)
        ttff_data = gutils.process_ttff_by_gtw_gpstool(self.ad, begin_time, self.pixel_lab_location)
        result = gutils.check_ttff_data(self.ad, ttff_data, ttff_mode="Cold Start",
                                        criteria=self.supl_cs_criteria)

        asserts.assert_true(result, "TTFF fails to reach designated criteria")

    @test_tracker_info(uuid="a748af8b-e1eb-4ec6-bde3-74bcefa1c680")
    def test_supl_modem_ssr(self):
        """Verify SUPL functionality after modem silent reboot /
        GPS daemons restart.

        Steps:
            1. Trigger modem crash by adb/Restart GPS daemons by killing PID.
            2. Wait 1 minute for modem to recover.
            3. SUPL TTFF Cold Start for 3 iteration.
            4. Repeat Step 1. to Step 3. for 5 times.

        Expected Results:
            All SUPL TTFF Cold Start results should be within supl_cs_criteria.
        """
        supl_ssr_test_result_all = []
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        for times in range(1, 6):
            begin_time = get_current_epoch_time()
            if gutils.check_chipset_vendor_by_qualcomm(self.ad):
                test_info = "Modem SSR"
                gutils.gnss_trigger_modem_ssr_by_mds(self.ad)
            else:
                test_info = "restarting GPS daemons"
                gutils.restart_gps_daemons(self.ad)
            if not verify_internet_connection(self.ad.log, self.ad, retries=3,
                                              expected_state=True):
                raise signals.TestFailure("Fail to connect to LTE network.")
            gutils.process_gnss_by_gtw_gpstool(self.ad, self.standalone_cs_criteria)
            gutils.start_ttff_by_gtw_gpstool(self.ad, ttff_mode="cs", iteration=3)
            ttff_data = gutils.process_ttff_by_gtw_gpstool(self.ad, begin_time,
                                                    self.pixel_lab_location)
            supl_ssr_test_result = gutils.check_ttff_data(
                self.ad, ttff_data, ttff_mode="Cold Start",
                criteria=self.supl_cs_criteria)
            self.ad.log.info("SUPL after %s test %d times -> %s" % (
                test_info, times, supl_ssr_test_result))
            supl_ssr_test_result_all.append(supl_ssr_test_result)

        asserts.assert_true(all(supl_ssr_test_result_all),
                            "TTFF fails to reach designated criteria")

    @test_tracker_info(uuid="085b86a9-0212-4c0f-8ca1-2e467a0a2e6e")
    def test_supl_after_regain_gnss_signal(self):
        """Verify SUPL functionality after regain GNSS signal.

        Steps:
            1. Get location fixed.
            2  Let device do GNSS tracking for 1 minute.
            3. Set attenuation value to block GNSS signal.
            4. Let DUT stay in no GNSS signal for 5 minutes.
            5. Set attenuation value to regain GNSS signal.
            6. Try to get location reported again.
            7. Repeat Step 1. to Step 6. for 5 times.

        Expected Results:
            After setting attenuation value to 10 (GPS signal regain),
            DUT could get location fixed again.
        """
        supl_no_gnss_signal_all = []
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        for times in range(1, 6):
            gutils.process_gnss_by_gtw_gpstool(self.ad, self.standalone_cs_criteria)
            self.ad.log.info("Let device do GNSS tracking for 1 minute.")
            time.sleep(60)
            gutils.set_attenuator_gnss_signal(self.ad, self.attenuators,
                                              self.no_gnss_signal_attenuation)
            self.ad.log.info("Let device stay in no GNSS signal for 5 minutes.")
            time.sleep(300)
            gutils.set_attenuator_gnss_signal(self.ad, self.attenuators,
                                              self.default_gnss_signal_attenuation)
            supl_no_gnss_signal = gutils.check_location_api(self.ad, retries=3)
            gutils.start_gnss_by_gtw_gpstool(self.ad, False)
            self.ad.log.info("SUPL without GNSS signal test %d times -> %s"
                             % (times, supl_no_gnss_signal))
            supl_no_gnss_signal_all.append(supl_no_gnss_signal)

        asserts.assert_true(all(supl_no_gnss_signal_all),
                            "Fail to get location update")

    @test_tracker_info(uuid="3ff2f2fa-42d8-47fa-91de-060816cca9df")
    def test_supl_ttff_cs_weak_gnss_signal(self):
        """Verify SUPL functionality of TTFF Cold Start under weak GNSS signal.

        Steps:
            1. Set attenuation value to weak GNSS signal.
            2. Kill XTRA/LTO daemon to support SUPL only case.
            3. SUPL TTFF Cold Start for 10 iteration.

        Expected Results:
            All SUPL TTFF Cold Start results should be less than
            weak_signal_supl_cs_criteria.
        """
        self.supl_ttff_weak_gnss_signal("cs", self.weak_signal_supl_cs_criteria)

    @test_tracker_info(uuid="d72364d4-dad8-4d46-8190-87183def9822")
    def test_supl_ttff_ws_weak_gnss_signal(self):
        """Verify SUPL functionality of TTFF Warm Start under weak GNSS signal.

        Steps:
            1. Set attenuation value to weak GNSS signal.
            2. Kill XTRA/LTO daemon to support SUPL only case.
            3. SUPL TTFF Warm Start for 10 iteration.

        Expected Results:
            All SUPL TTFF Warm Start results should be less than
            weak_signal_supl_ws_criteria.
        """
        self.supl_ttff_weak_gnss_signal("ws", self.weak_signal_supl_ws_criteria)

    @test_tracker_info(uuid="aeb95733-9829-470d-bfc7-e3b059bf881f")
    def test_supl_ttff_hs_weak_gnss_signal(self):
        """Verify SUPL functionality of TTFF Hot Start under weak GNSS signal.

        Steps:
            1. Set attenuation value to weak GNSS signal.
            2. Kill XTRA/LTO daemon to support SUPL only case.
            3. SUPL TTFF Hot Start for 10 iteration.

        Expected Results:
            All SUPL TTFF Hot Start results should be less than
            weak_signal_supl_hs_criteria.
        """
        self.supl_ttff_weak_gnss_signal("hs", self.weak_signal_supl_hs_criteria)

    @test_tracker_info(uuid="4ad4a371-949a-42e1-b1f4-628c79fa8ddc")
    def test_supl_factory_reset(self):
        """Verify SUPL functionality after factory reset.

        Steps:
            1. Factory reset device.
            2. Kill XTRA/LTO daemon to support SUPL only case.
            3. SUPL TTFF Cold Start for 10 iteration.
            4. Repeat Step 1. to Step 3. for 3 times.

        Expected Results:
            All SUPL TTFF Cold Start results should be within supl_cs_criteria.
        """
        for times in range(1, 4):
            gutils.fastboot_factory_reset(self.ad, True)
            self.ad.unlock_screen(password=None)
            self.init_device()
            self.ad.log.info("SUPL after factory reset round %d" % times)
            self.run_ttff(mode="cs", criteria=self.supl_cs_criteria)
            self.ad.log.info("SUPL after Factory Reset round %d -> PASS" % times)

    @test_tracker_info(uuid="9f565b32-9938-42c0-a29d-f4d28b5f4d75")
    def test_supl_system_server_restart(self):
        """Verify SUPL functionality after system server restart.

        Steps:
            1. Kill XTRA/LTO daemon to support SUPL only case.
            2. Get location fixed within supl_cs_criteria.
            3. Restarts android runtime.
            4. Get location fixed within supl_cs_criteria.

        Expected Results:
            Location fixed within supl_cs_criteria.
        """
        overall_test_result = []
        gutils.start_qxdm_and_tcpdump_log(self.ad, self.collect_logs)
        for test_loop in range(1, 6):
            gutils.process_gnss_by_gtw_gpstool(self.ad, self.supl_cs_criteria)
            gutils.start_gnss_by_gtw_gpstool(self.ad, False)
            self.ad.restart_runtime()
            self.ad.unlock_screen(password=None)
            test_result = gutils.process_gnss_by_gtw_gpstool(self.ad, self.supl_cs_criteria)
            gutils.start_gnss_by_gtw_gpstool(self.ad, False)
            self.ad.log.info("Iteration %d => %s" % (test_loop, test_result))
            overall_test_result.append(test_result)

        asserts.assert_true(all(overall_test_result),
                            "SUPL fail after system server restart.")

    @test_tracker_info(uuid="4a364e0f-926d-45ff-b3f0-733b5e30e073")
    def test_cs_ttff_supl_over_wifi_with_mobile_data_off(self):
        """ Test supl can works through wifi with mobile data off

        Test steps are executed in the following sequence.
        - Turn off mobile data
        - Connect to wifi
        - Run SUPL CS TTFF
        """
        # We can't push real project name into git repo, so I will add the desired projects name
        # into configuration file on g3 and read it from test cases
        self.runs_on_projects(self.project_limit_lte)

        self.connect_to_wifi_with_mobile_data_off()

        self.run_ttff(mode="cs", criteria=self.supl_cs_criteria)

    @test_tracker_info(uuid="4adce337-b79b-4085-9d3d-7cdd88dc4643")
    def test_hs_ttff_supl_over_wifi_with_mobile_data_off(self):
        """ Test supl can works through wifi with mobile data off

        Test steps are executed in the following sequence.
        - Turn off mobile data
        - Connect to wifi
        - Run SUPL HS TTFF
        """
        self.runs_on_projects(self.project_limit_lte)

        self.connect_to_wifi_with_mobile_data_off()

        self.run_ttff("hs", self.supl_hs_criteria)

    @test_tracker_info(uuid="18c316ef-6a70-4709-a71c-12ec3e5326d6")
    def test_cs_ttff_supl_over_wifi_with_airplane_mode_on(self):
        """ Test supl can works through wifi with airplane mode on

        Test steps are executed in the following sequence.
        - Turn on airplane mode
        - Connect to wifi
        - Run SUPL CS TTFF
        """
        self.runs_on_projects(self.project_limit_lte_btwifi)

        self.connect_to_wifi_with_airplane_mode_on()

        self.run_ttff(mode="cs", criteria=self.supl_cs_criteria)

    @test_tracker_info(uuid="afcab5bd-b2a9-4846-929c-3aa2596a6044")
    def test_ws_ttff_supl_over_wifi_with_airplane_mode_on(self):
        """ Test supl can works through wifi with airplane mode on

        Test steps are executed in the following sequence.
        - Turn on airplane mode
        - Connect to wifi
        - Run SUPL WS TTFF
        """
        self.runs_on_projects(self.project_limit_lte_btwifi)

        self.connect_to_wifi_with_airplane_mode_on()

        self.run_ttff("ws", self.supl_ws_criteria)

    @test_tracker_info(uuid="b13b8589-946b-48c7-b1a6-7399b4b12440")
    def test_supl_with_wifi_connected_and_mobile_data_on(self):
        """ Test supl can works on both wifi / mobile data features are turned on

        Test steps are executed in the following sequence.
        - Connect to wifi
        - Run SUPL CS TTFF
        """
        self.runs_on_projects(self.project_limit_lte)

        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

        self.run_ttff(mode="cs", criteria=self.supl_cs_criteria)
