#!/usr/bin/env python3.4
#
#   Copyright 2020 - Google
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
"""
    Test Script for 5G Tethering scenarios
"""

import time

from acts.utils import rand_ascii_str
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import RAT_5G
from acts_contrib.test_utils.tel.tel_defines import TETHERING_PASSWORD_HAS_ESCAPE
from acts_contrib.test_utils.tel.tel_defines import TETHERING_SPECIAL_SSID_LIST
from acts_contrib.test_utils.tel.tel_defines import TETHERING_SPECIAL_PASSWORD_LIST
from acts_contrib.test_utils.tel.tel_data_utils import run_stress_test
from acts_contrib.test_utils.tel.tel_data_utils import test_wifi_tethering
from acts_contrib.test_utils.tel.tel_data_utils import test_setup_tethering
from acts_contrib.test_utils.tel.tel_data_utils import verify_toggle_apm_tethering_internet_connection
from acts_contrib.test_utils.tel.tel_data_utils import verify_tethering_entitlement_check
from acts_contrib.test_utils.tel.tel_data_utils import test_start_wifi_tethering_connect_teardown
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_default_state
from acts_contrib.test_utils.tel.tel_test_utils import WIFI_CONFIG_APBAND_5G
from acts_contrib.test_utils.tel.tel_test_utils import WIFI_CONFIG_APBAND_2G
from acts_contrib.test_utils.tel.tel_test_utils import wifi_reset
from acts_contrib.test_utils.tel.tel_5g_utils import provision_device_for_5g


class Nsa5gTetheringTest(TelephonyBaseTest):
    def setup_class(self):
        super().setup_class()
        self.stress_test_number = self.get_stress_test_number()
        self.provider = self.android_devices[0]
        self.clients = self.android_devices[1:]

    def setup_test(self):
        TelephonyBaseTest.setup_test(self)
        self.number_of_devices = 1

    def teardown_class(self):
        TelephonyBaseTest.teardown_class(self)

    """ Tests Begin """

    @test_tracker_info(uuid="c7957e52-d5e5-499b-b387-fced88fda237")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tethering_to_5gwifi(self):
        """WiFi Tethering test: 5G NSA to WiFI 5G Tethering

        1. DUT in 5G NSA mode, attached.
        2. DUT start 5G WiFi Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        return test_wifi_tethering(self.log,
                                   self.provider,
                                   self.clients,
                                   self.clients,
                                   RAT_5G,
                                   WIFI_CONFIG_APBAND_5G,
                                   check_interval=10,
                                   check_iteration=10)

    @test_tracker_info(uuid="0af10a6b-7c01-41fd-95ce-d839a787aa98")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tethering_to_2gwifi(self):
        """WiFi Tethering test: 5G NSA to WiFI 2G Tethering

        1. DUT in 5G NSA mode, attached.
        2. DUT start 2.4G WiFi Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        return test_wifi_tethering(self.log,
                                   self.provider,
                                   self.clients,
                                   self.clients,
                                   RAT_5G,
                                   WIFI_CONFIG_APBAND_2G,
                                   check_interval=10,
                                   check_iteration=10)

    @test_tracker_info(uuid="d7ab31d5-5f96-4b48-aa92-810e6cfcf845")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_wifi_tethering_toggle_apm(self):
        """WiFi Tethering test: Toggle APM during active WiFi 2.4G Tethering from 5G NSA

        1. DUT in 5G NSA mode, idle.
        2. DUT start 2.4G WiFi Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB
        5. DUT toggle APM on, verify WiFi tethering stopped, PhoneB lost WiFi connection.
        6. DUT toggle APM off, verify PhoneA have cellular data and Internet connection.

        Returns:
            True if success.
            False if failed.
        """
        try:
            ssid = rand_ascii_str(10)
            if not test_wifi_tethering(self.log,
                                       self.provider,
                                       self.clients,
                                       [self.clients[0]],
                                       RAT_5G,
                                       WIFI_CONFIG_APBAND_2G,
                                       check_interval=10,
                                       check_iteration=2,
                                       do_cleanup=False,
                                       ssid=ssid):
                self.log.error("WiFi Tethering failed.")
                return False

            if not verify_toggle_apm_tethering_internet_connection(self.log,
                                                                   self.provider,
                                                                   self.clients,
                                                                   ssid):
                return False
        finally:
            self.clients[0].droid.telephonyToggleDataConnection(True)
            wifi_reset(self.log, self.clients[0])
        return True

    @test_tracker_info(uuid="2be31ba7-f69c-410b-86d1-daaeda892533")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tethering_entitlement_check(self):
        """5G NSA Tethering Entitlement Check Test

        Get tethering entitlement check result.

        Returns:
            True if entitlement check returns True.
        """

        if not provision_device_for_5g(self.log, self.provider):
            return False
        return verify_tethering_entitlement_check(self.log,
                                                  self.provider)

    @test_tracker_info(uuid="f07c316c-dbab-4c95-8bec-2a2fc029d5cd")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tethering_to_2gwifi_stress(self):
        """Stress Test 5G NSA to WiFI 2.4G Tethering

        This is a stress test for "test_tethering_4g_to_2gwifi".
        Default MINIMUM_SUCCESS_RATE is set to 95%.

        Returns:
            True stress pass rate is higher than MINIMUM_SUCCESS_RATE.
            False otherwise.
        """
        def precondition():
            ensure_phones_default_state(self.log, self.android_devices)

        def test_case():
            return test_wifi_tethering(self.log,
                                       self.provider,
                                       self.clients,
                                       self.clients,
                                       RAT_5G,
                                       WIFI_CONFIG_APBAND_2G,
                                       check_interval=10,
                                       check_iteration=10)
        return run_stress_test(self.log, self.stress_test_number, precondition, test_case)

    @test_tracker_info(uuid="bbe9175d-8781-4b31-9962-21abb9441022")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tethering_wifi_ssid_quotes(self):
        """WiFi Tethering test: 5G NSA wifi tethering SSID name have quotes.
        1. Set SSID name have double quotes.
        2. Start LTE to WiFi (2.4G) tethering.
        3. Verify tethering.

        Returns:
            True if success.
            False if failed.
        """
        ssid = "\"" + rand_ascii_str(10) + "\""
        self.log.info(
            "Starting WiFi Tethering test with ssid: {}".format(ssid))

        return test_wifi_tethering(self.log,
                                   self.provider,
                                   self.clients,
                                   self.clients,
                                   RAT_5G,
                                   WIFI_CONFIG_APBAND_2G,
                                   check_interval=10,
                                   check_iteration=10,
                                   ssid=ssid)

    @test_tracker_info(uuid="678c6b04-6733-41e1-bb0c-af8c9d1183cb")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tethering_wifi_password_escaping_characters(self):
        """WiFi Tethering test: 5G NSA wifi tethering password have escaping characters.
        1. Set password have escaping characters.
            e.g.: '"DQ=/{Yqq;M=(^_3HzRvhOiL8S%`]w&l<Qp8qH)bs<4E9v_q=HLr^)}w$blA0Kg'
        2. Start LTE to WiFi (2.4G) tethering.
        3. Verify tethering.

        Returns:
            True if success.
            False if failed.
        """

        password = TETHERING_PASSWORD_HAS_ESCAPE
        self.log.info(
            "Starting WiFi Tethering test with password: {}".format(password))

        return test_wifi_tethering(self.log,
                                   self.provider,
                                   self.clients,
                                   self.clients,
                                   RAT_5G,
                                   WIFI_CONFIG_APBAND_2G,
                                   check_interval=10,
                                   check_iteration=10,
                                   password=password)

    @test_tracker_info(uuid="eacc5412-fe75-400b-aba9-c0c38bdfff71")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tethering_wifi_ssid(self):
        """WiFi Tethering test: start 5G NSA WiFi tethering with all kinds of SSIDs.

        For each listed SSID, start WiFi tethering on DUT, client connect WiFi,
        then tear down WiFi tethering.

        Returns:
            True if WiFi tethering succeed on all SSIDs.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Setup Failed.")
            return False
        ssid_list = TETHERING_SPECIAL_SSID_LIST
        fail_list = {}
        self.number_of_devices = 2
        for ssid in ssid_list:
            password = rand_ascii_str(8)
            self.log.info("SSID: <{}>, Password: <{}>".format(ssid, password))
            if not test_start_wifi_tethering_connect_teardown(self.log,
                                                              self.provider,
                                                              self.clients[0],
                                                              ssid,
                                                              password):
                fail_list[ssid] = password

        if len(fail_list) > 0:
            self.log.error("Failed cases: {}".format(fail_list))
            return False
        else:
            return True

    @test_tracker_info(uuid="249cfa53-edb2-4d9c-8f4f-8291bf22fb36")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tethering_wifi_password(self):
        """WiFi Tethering test: start 5G NSA WiFi tethering with all kinds of passwords.

        For each listed password, start WiFi tethering on DUT, client connect WiFi,
        then tear down WiFi tethering.

        Returns:
            True if WiFi tethering succeed on all passwords.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Setup Failed.")
            return False
        password_list = TETHERING_SPECIAL_PASSWORD_LIST
        fail_list = {}
        self.number_of_devices = 2
        for password in password_list:
            ssid = rand_ascii_str(8)
            self.log.info("SSID: <{}>, Password: <{}>".format(ssid, password))
            if not test_start_wifi_tethering_connect_teardown(self.log,
                                                              self.provider,
                                                              self.clients[0],
                                                              ssid,
                                                              password):
                fail_list[ssid] = password

        if len(fail_list) > 0:
            self.log.error("Failed cases: {}".format(fail_list))
            return False
        else:
            return True

    """ Tests End """
