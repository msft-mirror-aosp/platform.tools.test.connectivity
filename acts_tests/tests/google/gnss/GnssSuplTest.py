import re

from acts import signals
from acts.base_test import BaseTestClass
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.gnss import gnss_test_utils as gutils
from acts_contrib.test_utils.gnss import supl
from acts_contrib.test_utils.wifi import wifi_test_utils as wutils
from acts_contrib.test_utils.tel.tel_logging_utils import get_tcpdump_log
from acts_contrib.test_utils.tel.tel_logging_utils import stop_adb_tcpdump
from acts_contrib.test_utils.tel.tel_logging_utils import get_tcpdump_log
from acts_contrib.test_utils.tel.tel_test_utils import verify_internet_connection


class GnssSuplTest(BaseTestClass):
    def setup_class(self):
        super().setup_class()
        self.ad = self.android_devices[0]
        req_params = ["pixel_lab_network",
                      "supl_cs_criteria",
                      "supl_ws_criteria",
                      "supl_hs_criteria",
                      "default_gnss_signal_attenuation",
                      "pixel_lab_location",
                      "qdsp6m_path",
                      "collect_logs", "ttff_test_cycle",
                      "project_limit_lte", "project_limit_lte_btwifi"]
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
        gutils.disable_ramdump(self.ad)

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

    def teardown_test(self):
        if self.collect_logs:
            gutils.stop_pixel_logger(self.ad)
            stop_adb_tcpdump(self.ad)
            gutils.set_attenuator_gnss_signal(self.ad, self.attenuators,
                                              self.default_gnss_signal_attenuation)

    def on_fail(self, test_name, begin_time):
        if self.collect_logs:
            self.ad.take_bug_report(test_name, begin_time)
            gutils.get_gnss_qxdm_log(self.ad, self.qdsp6m_path)
            get_tcpdump_log(self.ad, test_name, begin_time)

    # TODO: (diegowchung) GnssFunctionTest has similar function, need to handle the duplication
    def run_ttff(self, mode, criteria):
        """Verify SUPL TTFF functionality.

        Args:
            mode: "cs", "ws" or "hs"
            criteria: Criteria for the test.
        """
        gutils.start_qxdm_and_tcpdump_log(self.ad, enable=self.collect_logs)
        gutils.run_ttff_via_gtw_gpstool(self.ad, mode, criteria, self.ttff_test_cycle,
                                        self.pixel_lab_location)

    def connect_to_wifi_with_mobile_data_off(self):
        gutils.set_mobile_data(self.ad, False)
        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

    def connect_to_wifi_with_airplane_mode_on(self):
        self.ad.droid.connectivityToggleAirplaneMode(True)
        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

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

        self.run_ttff("cs", self.supl_cs_criteria)

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

        self.run_ttff("cs", self.supl_cs_criteria)

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

        self.run_ttff("cs", self.supl_cs_criteria)
