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

from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.bt.bt_test_utils import disable_bluetooth
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import RAT_5G
from acts_contrib.test_utils.tel.tel_defines import MAX_WAIT_TIME_NW_SELECTION
from acts_contrib.test_utils.tel.tel_defines import NETWORK_SERVICE_DATA
from acts_contrib.test_utils.tel.tel_data_utils import wifi_tethering_setup_teardown
from acts_contrib.test_utils.tel.tel_test_utils import WIFI_CONFIG_APBAND_5G
from acts_contrib.test_utils.tel.tel_test_utils import WIFI_CONFIG_APBAND_2G
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_test_utils import wifi_toggle_state
from acts_contrib.test_utils.tel.tel_test_utils import ensure_network_generation
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_test_utils import stop_wifi_tethering
from acts_contrib.test_utils.tel.tel_test_utils import wait_for_cell_data_connection
from acts_contrib.test_utils.tel.tel_test_utils import verify_internet_connection
from acts_contrib.test_utils.tel.tel_5g_utils import is_current_network_5g_nsa
from acts_contrib.test_utils.tel.tel_5g_utils import set_preferred_mode_for_5g

class Nsa5gTetheringTest(TelephonyBaseTest):
    def setup_class(self):
        super().setup_class()
        self.provider = self.android_devices[0]
        self.clients = self.android_devices[1:]

    def setup_test(self):
        TelephonyBaseTest.setup_test(self)
        self.number_of_devices = 1

    def teardown_class(self):
        TelephonyBaseTest.teardown_class(self)


    def _test_setup_tethering(self, network_generation=None):
        """Pre setup steps for WiFi tethering test.

        Ensure all ads are idle.
        Ensure tethering provider:
            turn off APM, turn off WiFI, turn on Data.
            have Internet connection, no active ongoing WiFi tethering.

        Returns:
            True if success.
            False if failed.
        """
        self.number_of_devices = None
        ensure_phones_idle(self.log, self.android_devices)
        wifi_toggle_state(self.log, self.provider, False)
        if network_generation == RAT_5G:
            # Attach nsa5g
            set_preferred_mode_for_5g(self.provider)
            if not is_current_network_5g_nsa(self.provider):
                self.provider.log.error("Provider not attached on 5G NSA")
                return False
        elif network_generation:
            if not ensure_network_generation(
                    self.log, self.provider, network_generation,
                    MAX_WAIT_TIME_NW_SELECTION, NETWORK_SERVICE_DATA):
                self.provider.log.error("Provider failed to connect to %s.",
                                        network_generation)
                return False
        else:
            self.log.debug("Skipping network generation since it is None")
        self.provider.log.info(
            "Set provider Airplane Off, Wifi Off, Bluetooth Off, Data On.")
        toggle_airplane_mode(self.log, self.provider, False)
        self.provider.droid.telephonyToggleDataConnection(True)
        self.provider.log.info("Provider disable wifi")
        wifi_toggle_state(self.log, self.provider, False)
        # Turn off active SoftAP if any.
        if self.provider.droid.wifiIsApEnabled():
            self.provider.log.info("Disable provider wifi tethering")
            stop_wifi_tethering(self.log, self.provider)
        self.provider.log.info("Provider disable bluetooth")
        disable_bluetooth(self.provider.droid)
        time.sleep(10)
        for ad in self.clients:
            ad.log.info(
                "Set client Airplane Off, Wifi Off, Bluetooth Off, Data Off.")
            toggle_airplane_mode(self.log, ad, False)
            ad.log.info("Client disable data")
            ad.droid.telephonyToggleDataConnection(False)
            ad.log.info("Client disable bluetooth")
            disable_bluetooth(ad.droid)
            ad.log.info("Client disable wifi")
            wifi_toggle_state(self.log, ad, False)
        if not wait_for_cell_data_connection(self.log, self.provider, True):
            self.provider.log.error(
                "Provider failed to enable data connection.")
            return False
        time.sleep(10)
        self.log.info("Verify internet")
        if not self._test_internet_connection(
                client_status=False, provider_status=True):
            self.log.error("Internet connection check failed before tethering")
            return False
        return True

    def _test_internet_connection(self,
                                  client_status=True,
                                  provider_status=True):
        client_retry = 10 if client_status else 1
        for client in self.clients:
            if not verify_internet_connection(
                    self.log,
                    client,
                    retries=client_retry,
                    expected_state=client_status):
                client.log.error("client internet connection state is not %s",
                                 client_status)
                return False
            else:
                client.log.info("client internet connection state is %s",
                                client_status)
        if not verify_internet_connection(
                self.log, self.provider, retries=3,
                expected_state=provider_status):
            self.provider.log.error(
                "provider internet connection is not %s" % provider_status)
            return False
        else:
            self.provider.log.info(
                "provider internet connection is %s" % provider_status)
        return True


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
        if not self._test_setup_tethering(RAT_5G):
            self.log.error("Verify 5G NSA Internet access failed.")
            return False

        return wifi_tethering_setup_teardown(
            self.log,
            self.provider,
            self.clients,
            ap_band=WIFI_CONFIG_APBAND_5G,
            check_interval=10,
            check_iteration=10)


    @test_tracker_info(uuid="0af10a6b-7c01-41fd-95ce-d839a787aa98")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tethering_to_2gwifi(self):
        """WiFi Tethering test: 5G NSA to WiFI 2G Tethering

        1. DUT in 5G NSA mode, attached.
        2. DUT start 5G WiFi Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        if not self._test_setup_tethering(RAT_5G):
            self.log.error("Verify 5G NSA Internet access failed.")
            return False

        return wifi_tethering_setup_teardown(
            self.log,
            self.provider,
            self.clients,
            ap_band=WIFI_CONFIG_APBAND_2G,
            check_interval=10,
            check_iteration=10)


    """ Tests End """
