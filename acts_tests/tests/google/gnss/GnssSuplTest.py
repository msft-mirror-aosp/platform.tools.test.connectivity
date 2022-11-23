from multiprocessing import Process
import time

from acts import asserts
from acts import signals
from acts.base_test import BaseTestClass
from acts.test_decorators import test_tracker_info
from acts.utils import get_current_epoch_time
from acts_contrib.test_utils.gnss import gnss_test_utils as gutils
from acts_contrib.test_utils.gnss import supl
from acts_contrib.test_utils.gnss import gnss_defines
from acts_contrib.test_utils.tel.tel_data_utils import http_file_download_by_sl4a
from acts_contrib.test_utils.tel.tel_logging_utils import get_tcpdump_log
from acts_contrib.test_utils.tel.tel_logging_utils import stop_adb_tcpdump
from acts_contrib.test_utils.tel.tel_logging_utils import get_tcpdump_log
from acts_contrib.test_utils.tel.tel_test_utils import check_call_state_connected_by_adb
from acts_contrib.test_utils.tel.tel_test_utils import verify_internet_connection
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
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
            "qdsp6m_path", "collect_logs", "ttff_test_cycle", "weak_gnss_signal_attenuation",
            "supl_capabilities", "no_gnss_signal_attenuation", "set_attenuator"
        ]
        self.unpack_userparams(req_param_names=req_params)
        # create hashmap for SSID
        self.ssid_map = {}
        for network in self.pixel_lab_network:
            SSID = network["SSID"]
            self.ssid_map[SSID] = network
        self.init_device()

    def only_brcm_device_runs_wifi_case(self):
        """SUPL over wifi is only supported by BRCM devices, for QUAL device, skip the test.
        """
        if gutils.check_chipset_vendor_by_qualcomm(self.ad):
            raise signals.TestSkip("Qualcomm device doesn't support SUPL over wifi")

    def wearable_btwifi_should_skip_mobile_data_case(self):
        if gutils.is_wearable_btwifi(self.ad):
            raise signals.TestSkip("Skip mobile data case for BtWiFi sku")

    def init_device(self):
        """Init GNSS test devices for SUPL suite."""
        gutils._init_device(self.ad)
        gutils.disable_vendor_orbit_assistance_data(self.ad)
        gutils.enable_supl_mode(self.ad)
        self.enable_supl_over_wifi()
        gutils.reboot(self.ad)

    def enable_supl_over_wifi(self):
        if not gutils.check_chipset_vendor_by_qualcomm(self.ad):
            supl.set_supl_over_wifi_state(self.ad, turn_on=True)

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
        gutils.log_current_epoch_time(self.ad, "test_end_time")

    def on_fail(self, test_name, begin_time):
        if self.collect_logs:
            self.ad.take_bug_report(test_name, begin_time)
            gutils.get_gnss_qxdm_log(self.ad, self.qdsp6m_path)
            self.get_brcm_gps_xml_to_sponge()
            get_tcpdump_log(self.ad, test_name, begin_time)

    def get_brcm_gps_xml_to_sponge(self):
        # request from b/250506003 - to check the SUPL setting
        if not gutils.check_chipset_vendor_by_qualcomm(self.ad):
            self.ad.pull_files(gnss_defines.BCM_GPS_XML_PATH, self.ad.device_log_path)

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
        toggle_airplane_mode(self.ad.log, self.ad, new_state=True)
        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

    @test_tracker_info(uuid="6c794396-46e8-4674-8985-49a7b3059372")
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


    @test_tracker_info(uuid="ae8b6d54-bdd6-44a1-b1fa-4e90e0318080")
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

    @test_tracker_info(uuid="65f25e0b-c6d0-47c5-ab1f-0b02b621411d")
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

    @test_tracker_info(uuid="a2267586-97e9-465c-8d3a-22882c8671e7")
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

    @test_tracker_info(uuid="ed815ab3-2470-4a2b-b29a-434c38c24c24")
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

    @test_tracker_info(uuid="7015ff04-05e6-4e89-ae4a-da53573ae4c3")
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

    @test_tracker_info(uuid="47a44eb7-4437-4fc2-b5dd-8e55fcd1a91e")
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

    @test_tracker_info(uuid="e07463a9-5cf7-4ac9-92b8-5f0c0b6c6f89")
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

    @test_tracker_info(uuid="156d84c5-8fc6-436a-bc38-ef6c699b6f29")
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

    @test_tracker_info(uuid="aa644d09-645a-415e-9cf1-5fd067607c24")
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

    @test_tracker_info(uuid="05ba12b4-4953-48d6-b905-3fce743afcd9")
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

    @test_tracker_info(uuid="11c0e96f-a9c4-47b9-8caa-bfa3c46b44bd")
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

    @test_tracker_info(uuid="85bd25e8-48b3-4cc2-a6ca-42c5106f0cff")
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
            if not verify_internet_connection(self.ad.log, self.ad, retries=3, expected_state=True):
                raise signals.TestFailure("No internet connection on round {times}")
            self.ad.log.info("SUPL after factory reset round %d" % times)
            self.run_ttff(mode="cs", criteria=self.supl_cs_criteria)
            self.ad.log.info("SUPL after Factory Reset round %d -> PASS" % times)

    @test_tracker_info(uuid="bbe81393-f152-4f46-a9c6-692fb26f309e")
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

    @test_tracker_info(uuid="862e4c26-816d-4630-b8ff-35ffad66461d")
    def test_cs_ttff_supl_over_wifi_with_mobile_data_off(self):
        """ Test supl can works through wifi with mobile data off

        Test steps are executed in the following sequence.
        - Turn off mobile data
        - Connect to wifi
        - Run SUPL CS TTFF
        """
        self.only_brcm_device_runs_wifi_case()
        self.wearable_btwifi_should_skip_mobile_data_case()

        self.connect_to_wifi_with_mobile_data_off()

        self.run_ttff(mode="cs", criteria=self.supl_cs_criteria)

    @test_tracker_info(uuid="53864161-d17a-4fd9-897c-6d85401fab86")
    def test_hs_ttff_supl_over_wifi_with_mobile_data_off(self):
        """ Test supl can works through wifi with mobile data off

        Test steps are executed in the following sequence.
        - Turn off mobile data
        - Connect to wifi
        - Run SUPL HS TTFF
        """
        self.only_brcm_device_runs_wifi_case()
        self.wearable_btwifi_should_skip_mobile_data_case()

        self.connect_to_wifi_with_mobile_data_off()

        self.run_ttff("hs", self.supl_hs_criteria)

    @test_tracker_info(uuid="4b2882f8-2966-4b44-9a31-37318beb84bf")
    def test_cs_ttff_supl_over_wifi_with_airplane_mode_on(self):
        """ Test supl can works through wifi with airplane mode on

        Test steps are executed in the following sequence.
        - Turn on airplane mode
        - Connect to wifi
        - Run SUPL CS TTFF
        """
        self.only_brcm_device_runs_wifi_case()

        self.connect_to_wifi_with_airplane_mode_on()

        self.run_ttff(mode="cs", criteria=self.supl_cs_criteria)

    @test_tracker_info(uuid="a7f77afe-c82e-4b1b-ae54-e3fea17bf721")
    def test_ws_ttff_supl_over_wifi_with_airplane_mode_on(self):
        """ Test supl can works through wifi with airplane mode on

        Test steps are executed in the following sequence.
        - Turn on airplane mode
        - Connect to wifi
        - Run SUPL WS TTFF
        """
        self.only_brcm_device_runs_wifi_case()

        self.connect_to_wifi_with_airplane_mode_on()

        self.run_ttff("ws", self.supl_ws_criteria)

    @test_tracker_info(uuid="bc9de22f-90a0-4f2b-8052-cb4529f745e3")
    def test_supl_with_wifi_connected_and_mobile_data_on(self):
        """ Test supl can works on both wifi / mobile data features are turned on

        Test steps are executed in the following sequence.
        - Connect to wifi
        - Run SUPL CS TTFF
        """
        self.only_brcm_device_runs_wifi_case()
        self.wearable_btwifi_should_skip_mobile_data_case()

        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

        self.run_ttff(mode="cs", criteria=self.supl_cs_criteria)
