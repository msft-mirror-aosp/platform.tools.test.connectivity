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
        if self.collect_logs and \
            gutils.check_chipset_vendor_by_qualcomm(self.ad):
            self.flash_new_radio_or_mbn()
            self.push_gnss_cfg()
        self.init_device()

    def runs_on_projects(self, projects):
        """Check test case should be executed on specific projects
        Args:
            phone_projects: (list) list of project name,
                default value: [] -> runs on all projects
        """
        shell_result = self.ad.adb.shell("getprop | grep ro.build.product")
        regex = re.compile(":\s\[(\w+)\]")
        regex_result = re.search(regex, shell_result)
        actual_project = regex_result.group(1)

        if projects and actual_project not in projects:
            raise signals.TestSkip("Not expected project, skip the test. Runs on %s, got: %s" %
                                   (projects, actual_project))

    def init_device(self):
        """Init GNSS test devices for SUPL suite."""
        gutils.enable_gnss_verbose_logging(self.ad)
        gutils.enable_compact_and_particle_fusion_log(self.ad)
        gutils.prepare_gps_overlay(self.ad)
        gutils.enable_supl_mode(self.ad)
        gutils.set_screen_always_on(self.ad)
        gutils.check_location_service(self.ad)
        gutils.disable_private_dns_mode(self.ad)
        gutils.init_gtw_gpstool(self.ad)
        gutils.disable_vendor_orbit_assistance_data(self.ad)
        supl.set_supl_over_wifi_state(self.ad, turn_on=True)
        gutils.disable_ramdump(self.ad)

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

    @test_tracker_info(uuid="4a364e0f-926d-45ff-b3f0-733b5e30e073")
    def test_supl_over_wifi_with_mobile_data_off(self):
        """ Test supl can works through wifi with mobile data off
        1. Turn off mobile data
        2. Connect to wifi
        3. Run CS TTFF
        """
        # We can't push real project name into git repo, so I will add the desired projects name
        # into configuration file on g3 and read it from test cases
        self.runs_on_projects(self.project_limit_lte)

        gutils.set_mobile_data(self.ad, False)
        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

        self.run_ttff("cs", self.supl_cs_criteria)

    @test_tracker_info(uuid="18c316ef-6a70-4709-a71c-12ec3e5326d6")
    def test_supl_over_wifi_with_airplane_mode_on(self):
        """ Test supl can works through wifi with airplane mode on
        1. Turn on airplane mode
        2. Connect to wifi
        3. Run CS TTFF
        """
        self.runs_on_projects(self.project_limit_lte_btwifi)

        self.ad.droid.connectivityToggleAirplaneMode(True)
        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

        self.run_ttff("cs", self.supl_cs_criteria)

    @test_tracker_info(uuid="b13b8589-946b-48c7-b1a6-7399b4b12440")
    def test_supl_with_wifi_connected_and_mobile_data_on(self):
        """ Test supl can works on both wifi / mobile data features are turned on
        1. Connect to wifi
        2. Run CS TTFF
        """
        self.runs_on_projects(self.project_limit_lte)

        wutils.wifi_toggle_state(self.ad, True)
        gutils.connect_to_wifi_network(self.ad, self.ssid_map[self.pixel_lab_network[0]["SSID"]])

        self.run_ttff("cs", self.supl_cs_criteria)
