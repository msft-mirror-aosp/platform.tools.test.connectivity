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
    Test Script for 5G Data scenarios
"""

import time

from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import GEN_5G
from acts_contrib.test_utils.tel.tel_defines import MAX_WAIT_TIME_USER_PLANE_DATA
from acts_contrib.test_utils.tel.tel_defines import NETWORK_MODE_NR_LTE_GSM_WCDMA
from acts_contrib.test_utils.tel.tel_defines import NetworkCallbackCapabilitiesChanged
from acts_contrib.test_utils.tel.tel_defines import NetworkCallbackLost
from acts_contrib.test_utils.tel.tel_defines import NETWORK_SERVICE_DATA
from acts_contrib.test_utils.tel.tel_defines import RAT_2G
from acts_contrib.test_utils.tel.tel_defines import RAT_3G
from acts_contrib.test_utils.tel.tel_defines import RAT_4G
from acts_contrib.test_utils.tel.tel_defines import RAT_5G
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_ANDROID_STATE_SETTLING
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_BETWEEN_STATE_CHECK
from acts_contrib.test_utils.tel.tel_defines import \
    WAIT_TIME_DATA_STATUS_CHANGE_DURING_WIFI_TETHERING
from acts_contrib.test_utils.tel.tel_test_utils import break_internet_except_sl4a_port
from acts_contrib.test_utils.tel.tel_test_utils import check_data_stall_detection
from acts_contrib.test_utils.tel.tel_test_utils import check_data_stall_recovery
from acts_contrib.test_utils.tel.tel_test_utils import check_network_validation_fail
from acts_contrib.test_utils.tel.tel_test_utils import ensure_network_generation
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import get_current_override_network_type
from acts_contrib.test_utils.tel.tel_test_utils import get_device_epoch_time
from acts_contrib.test_utils.tel.tel_test_utils import iperf_test_by_adb
from acts_contrib.test_utils.tel.tel_test_utils import iperf_udp_test_by_adb
from acts_contrib.test_utils.tel.tel_test_utils import resume_internet_with_sl4a_port
from acts_contrib.test_utils.tel.tel_test_utils import set_preferred_network_mode_pref
from acts_contrib.test_utils.tel.tel_test_utils import test_data_browsing_failure_using_sl4a
from acts_contrib.test_utils.tel.tel_test_utils import test_data_browsing_success_using_sl4a
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_test_utils import verify_internet_connection
from acts_contrib.test_utils.tel.tel_test_utils import WIFI_CONFIG_APBAND_2G
from acts_contrib.test_utils.tel.tel_test_utils import WIFI_CONFIG_APBAND_5G
from acts_contrib.test_utils.tel.tel_test_utils import wifi_reset
from acts_contrib.test_utils.tel.tel_test_utils import wifi_toggle_state
from acts_contrib.test_utils.tel.tel_data_utils import browsing_test
from acts_contrib.test_utils.tel.tel_data_utils import data_connectivity_single_bearer
from acts_contrib.test_utils.tel.tel_data_utils import test_data_connectivity_multi_bearer
from acts_contrib.test_utils.tel.tel_data_utils import test_setup_tethering
from acts_contrib.test_utils.tel.tel_data_utils import test_tethering_wifi_and_voice_call
from acts_contrib.test_utils.tel.tel_data_utils import test_wifi_connect_disconnect
from acts_contrib.test_utils.tel.tel_data_utils import tethering_check_internet_connection
from acts_contrib.test_utils.tel.tel_data_utils import verify_bluetooth_tethering_connection
from acts_contrib.test_utils.tel.tel_data_utils import verify_for_network_callback
from acts_contrib.test_utils.tel.tel_data_utils import wifi_cell_switching
from acts_contrib.test_utils.tel.tel_data_utils import wifi_tethering_cleanup
from acts_contrib.test_utils.tel.tel_data_utils import wifi_tethering_setup_teardown
from acts_contrib.test_utils.tel.tel_5g_utils import is_current_network_5g_nsa
from acts_contrib.test_utils.tel.tel_5g_utils import provision_device_for_5g
from acts_contrib.test_utils.tel.tel_5g_utils import set_preferred_mode_for_5g
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_volte
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_volte



class Nsa5gDataTest(TelephonyBaseTest):
    def setup_class(self):
        super().setup_class()
        self.iperf_server_ip = self.user_params.get("iperf_server", '0.0.0.0')
        self.iperf_tcp_port = self.user_params.get("iperf_tcp_port", 0)
        self.iperf_udp_port = self.user_params.get("iperf_udp_port", 0)
        self.iperf_duration = self.user_params.get("iperf_duration", 60)

    def setup_test(self):
        TelephonyBaseTest.setup_test(self)
        self.provider = self.android_devices[0]
        self.clients = self.android_devices[1:]

    def teardown_class(self):
        TelephonyBaseTest.teardown_class(self)


    """ Tests Begin """

    @test_tracker_info(uuid="a73b749f-746c-4089-a8ad-4e47aed180f6")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_data_browsing(self):
        """ Verifying connectivity of internet and  browsing websites on 5G NSA network.

        Ensure
            1. ping to IP of websites is successful.
            2. http ping to IP of websites is successful.
            3. browsing websites is successful.
        Returns:
            True if pass; False if fail.
        """
        ad = self.android_devices[0]
        wifi_toggle_state(ad.log, ad, False)
        sub_id = ad.droid.subscriptionGetDefaultSubId()
        if not set_preferred_network_mode_pref(ad.log, ad, sub_id,
                                               NETWORK_MODE_NR_LTE_GSM_WCDMA):
            ad.log.error("Failed to set network mode to NSA")
            return False
        ad.log.info("Set network mode to NSA successfully")
        ad.log.info("Waiting for nsa5g NSA attach for 60 secs")
        if is_current_network_5g_nsa(ad, timeout=60):
            ad.log.info("Success! attached on nsa5g NSA")
        else:
            ad.log.error("Failure - expected NR_NSA, current %s",
                         get_current_override_network_type(ad))
            # Can't attach nsa5g NSA, exit test!
            return False
        for iteration in range(3):
            connectivity = False
            browsing = False
            ad.log.info("Attempt %d", iteration + 1)
            if not verify_internet_connection(self.log, ad):
                ad.log.error("Failed to connect to internet!")
            else:
                ad.log.info("Connect to internet successfully!")
                connectivity = True
            if not browsing_test(ad.log, ad):
                ad.log.error("Failed to browse websites!")
            else:
                ad.log.info("Successful to browse websites!")
                browsing = True
            if connectivity and browsing:
                return True
            time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)
        ad.log.error("5G NSA Connectivity and Data Browsing test FAIL for all 3 iterations")
        return False


    @test_tracker_info(uuid="c7727c26-b588-461f-851b-802bfa3a86af")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_data_stall_recovery(self):
        """ Verifies 5G NSA data stall

        Set Mode to 5G
        Wait for 5G attached on NSA
        Browse websites for success
        Trigger data stall and verify browsing fails
        Resume data and verify browsing success

        Returns:
            True if pass; False if fail.
        """
        ad = self.android_devices[0]
        result = True
        wifi_toggle_state(ad.log, ad, False)
        toggle_airplane_mode(ad.log, ad, False)

        if not provision_device_for_5g(ad.log, ad):
            return False

        cmd = ('ss -l -p -n | grep "tcp.*droid_script" | tr -s " " '
               '| cut -d " " -f 5 | sed s/.*://g')
        sl4a_port = ad.adb.shell(cmd)

        if not test_data_browsing_success_using_sl4a(ad.log, ad):
            ad.log.error("Browsing failed before the test, aborting!")
            return False

        begin_time = get_device_epoch_time(ad)
        break_internet_except_sl4a_port(ad, sl4a_port)

        if not test_data_browsing_failure_using_sl4a(ad.log, ad):
            ad.log.error("Browsing after breaking the internet, aborting!")
            result = False

        if not check_data_stall_detection(ad):
            ad.log.warning("NetworkMonitor unable to detect Data Stall")

        if not check_network_validation_fail(ad, begin_time):
            ad.log.warning("Unable to detect NW validation fail")

        if not check_data_stall_recovery(ad, begin_time):
            ad.log.error("Recovery was not triggered")
            result = False

        resume_internet_with_sl4a_port(ad, sl4a_port)
        time.sleep(MAX_WAIT_TIME_USER_PLANE_DATA)
        if not test_data_browsing_success_using_sl4a(ad.log, ad):
            ad.log.error("Browsing failed after resuming internet")
            result = False
        if result:
            ad.log.info("PASS - data stall over 5G NSA")
        else:
            ad.log.error("FAIL - data stall over 5G NSA")
        return result


    @test_tracker_info(uuid="bb823c3e-d84e-44b5-a9b4-89f65ab2d02c")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_metered_cellular(self):
        """ Verifies 5G Meteredness API

        Set Mode to 5G
        Wait for 5G attached on NSA
        Register for Connectivity callback
        Verify value of metered flag

        Returns:
            True if pass; False if fail.
        """
        ad = self.android_devices[0]
        try:
            wifi_toggle_state(ad.log, ad, False)
            toggle_airplane_mode(ad.log, ad, False)
            if not provision_device_for_5g(ad.log, ad):
                return False

            return verify_for_network_callback(ad.log, ad,
                NetworkCallbackCapabilitiesChanged, apm_mode=False)
        except Exception as e:
            ad.log.error(e)
            return False


    @test_tracker_info(uuid="80d7b388-3926-44ed-a7f1-3f94e6e315c7")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_metered_airplane(self):
        """ Verifies 5G Meteredness API

        Set Mode to 5G, Turn on Airplane mode
        Register for Connectivity callback
        Verify value of metered flag

        Returns:
            True if pass; False if fail.
        """
        ad = self.android_devices[0]
        try:
            wifi_toggle_state(ad.log, ad, False)
            set_preferred_mode_for_5g(ad)
            return verify_for_network_callback(ad.log, ad,
                NetworkCallbackLost, apm_mode=True)
        except Exception as e:
            ad.log.error(e)
            toggle_airplane_mode(ad.log, ad, False)
            time.sleep(WAIT_TIME_BETWEEN_STATE_CHECK)
            return False


    @test_tracker_info(uuid="192a605c-d7a9-4c34-800a-96a7d3177d7b")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_metered_wifi(self):
        """ Verifies 5G Meteredness API

        Set Mode to 5G, Wifi Connected
        Register for Connectivity callback
        Verify value of metered flag

        Returns:
            True if pass; False if fail.
        """
        ad = self.android_devices[0]
        try:
            toggle_airplane_mode(ad.log, ad, False)
            if not provision_device_for_5g(ad.log, ad):
                return False
            wifi_toggle_state(ad.log, ad, True)
            if not ensure_wifi_connected(ad.log, ad,
                                         self.wifi_network_ssid,
                                         self.wifi_network_pass):
                ad.log.error("WiFi connect fail.")
                return False
            return verify_for_network_callback(ad.log, ad,
                 NetworkCallbackCapabilitiesChanged)
        except Exception as e:
            ad.log.error(e)
            return False
        finally:
            wifi_toggle_state(ad.log, ad, False)


    @test_tracker_info(uuid="be0c110d-52d4-4af8-bf1c-96c4807d1f07")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_udp_throughput(self):
        """ Verifies UDP DL throughput over 5G

        Set Mode to 5G, Wifi Disconnected
        Verify device attached to 5G NSA
        Perform iperf test using UDP and measure throughput

        Returns:
            True if pass; False if fail.
        """
        ad = self.android_devices[0]
        try:
            toggle_airplane_mode(ad.log, ad, False)
            if not provision_device_for_5g(ad.log, ad):
                return False
            wifi_toggle_state(ad.log, ad, False)
            return iperf_udp_test_by_adb(ad.log,
                                         ad,
                                         self.iperf_server_ip,
                                         self.iperf_udp_port,
                                         True,
                                         self.iperf_duration)
        except Exception as e:
            ad.log.error(e)
            return False


    @test_tracker_info(uuid="47b87533-dc33-4c27-95ff-0b5316e6a193")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_tcp_throughput(self):
        """ Verifies TCP DL throughput over 5G

        Set Mode to 5G, Wifi Disconnected
        Verify device attached to 5G NSA
        Perform iperf test using TCP and measure throughput

        Returns:
            True if pass; False if fail.
        """
        ad = self.android_devices[0]
        try:
            toggle_airplane_mode(ad.log, ad, False)
            if not provision_device_for_5g(ad.log, ad):
                return False
            wifi_toggle_state(ad.log, ad, False)
            return iperf_test_by_adb(ad.log,
                                     ad,
                                     self.iperf_server_ip,
                                     self.iperf_tcp_port,
                                     True,
                                     self.iperf_duration)
        except Exception as e:
            ad.log.error(e)
            return False


    @test_tracker_info(uuid="79393af4-cbc1-4d00-8e02-fe76e8b28367")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_bursty_data(self):
        """ Verifies Bursty data transfer over 5G

        Set Mode to 5G, Wifi Disconnected
        Verify device attached to 5G NSA
        Perform iperf test using burst of data

        Returns:
            True if pass; False if fail.
        """
        ad = self.android_devices[0]
        try:
            toggle_airplane_mode(ad.log, ad, False)
            if not provision_device_for_5g(ad.log, ad):
                return False
            wifi_toggle_state(ad.log, ad, False)
            return iperf_udp_test_by_adb(ad.log,
                                         ad,
                                         self.iperf_server_ip,
                                         self.iperf_udp_port,
                                         True,
                                         self.iperf_duration,
                                         limit_rate="10M",
                                         pacing_timer="1000000")
        except Exception as e:
            ad.log.error(e)
            return False


    @test_tracker_info(uuid="cd1429e8-94d7-44de-ae48-68cf42f3246b")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_browsing(self):
        ad = self.android_devices[0]
        ad.log.info("Connect to NR and verify internet connection.")
        if not provision_device_for_5g(ad.log, ad):
            return False
        if not verify_internet_connection(ad.log, ad):
            return False

        return browsing_test(ad.log, ad)


    @test_tracker_info(uuid="7179f0f1-f0ca-4496-8f4a-7eebc616a41a")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_wifi_switching(self):
        """Test data connection network switching when phone camped on nsa 5G.

        Ensure phone is camped on nsa 5G
        Ensure WiFi can connect to live network,
        Airplane mode is off, data connection is on, WiFi is on.
        Turn off WiFi, verify data is on cell and browse to google.com is OK.
        Turn on WiFi, verify data is on WiFi and browse to google.com is OK.
        Turn off WiFi, verify data is on cell and browse to google.com is OK.

        Returns:
            True if pass.
        """
        ad = self.android_devices[0]
        return wifi_cell_switching(ad.log, ad, GEN_5G, self.wifi_network_ssid,
                                   self.wifi_network_pass)


    @test_tracker_info(uuid="75066e0a-0e2e-4346-a253-6ed11d1c4d23")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_multi_bearer(self):
        """Test nsa5G data connection before call and in call. (VoLTE call)

        Turn off airplane mode, disable WiFi, enable Cellular Data.
        Make sure phone in nsa5G, verify Internet.
        Initiate a voice call. verify Internet.
        Disable Cellular Data, verify Internet is inaccessible.
        Enable Cellular Data, verify Internet.
        Hangup Voice Call, verify Internet.

        Returns:
            True if success.
            False if failed.
        """
        ads = self.android_devices
        if not phone_setup_volte(ads[0].log, ads[0]):
            ads[0].log.error("Failed to setup VoLTE")
            return False
        return test_data_connectivity_multi_bearer(self.log, ads, GEN_5G)


    @test_tracker_info(uuid="e88b226e-3842-4c45-a33e-d4fee7d8f6f0")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa(self):
        """Test data connection in nsa5g.

        Turn off airplane mode, disable WiFi, enable Cellular Data.
        Ensure phone data generation is nsa 5g.
        Verify Internet.
        Disable Cellular Data, verify Internet is inaccessible.
        Enable Cellular Data, verify Internet.

        Returns:
            True if success.
            False if failed.
        """
        ad = self.android_devices[0]
        wifi_reset(ad.log, ad)
        wifi_toggle_state(ad.log, ad, False)
        return data_connectivity_single_bearer(ad.log, ad, GEN_5G)


    @test_tracker_info(uuid="4c70e09d-f215-4c5b-8c61-f9e9def43d30")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_wifi_not_associated(self):
        """Test data connection in nsa 5g.

        Turn off airplane mode, enable WiFi (but not connected), enable Cellular Data.
        Ensure phone data generation is nsa 5g.
        Verify Internet.
        Disable Cellular Data, verify Internet is inaccessible.
        Enable Cellular Data, verify Internet.

        Returns:
            True if success.
            False if failed.
        """
        ad = self.android_devices[0]
        wifi_reset(ad.log, ad)
        wifi_toggle_state(ad.log, ad, False)
        wifi_toggle_state(ad.log, ad, True)
        return data_connectivity_single_bearer(ad.log, ad, GEN_5G)


    @test_tracker_info(uuid="9feb4c81-17c6-46ed-9cf7-7aa3d5ae2da0")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_bluetooth_tethering(self):
        """Bluetooth Tethering test: nsa 5G to Bluetooth Tethering

        1. DUT in nsa 5G mode, idle.
        2. DUT start Bluetooth Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB
        5. Toggle provider bluetooth connection
        6. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Verify 5G Internet access failed.")
            return False

        return verify_bluetooth_tethering_connection(self.log, self.provider, self.clients)


    @test_tracker_info(uuid="db70c6ec-5edc-44c2-b61b-1c39516a7475")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_bluetooth_tethering_with_voice_call(self):
        """Bluetooth Tethering test: nsa 5G to Bluetooth Tethering

        1. DUT in nsa 5G mode, idle.
        2. DUT start Bluetooth Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB
        5. Verify provider and client are able to make or receive phone call
        6. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Verify 5G Internet access failed.")
            return False

        return verify_bluetooth_tethering_connection(self.log, self.provider, self.clients,
            toggle_tethering=False, toggle_bluetooth=False, voice_call=True)


    @test_tracker_info(uuid="12efb94f-7466-40e9-9a79-59b4074ab4dd")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_bluetooth_tethering_toggle_data(self):
        """Bluetooth Tethering test: nsa 5G to Bluetooth Tethering

        1. DUT in nsa 5G mode, idle.
        2. DUT start Bluetooth Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB
        5. Toggle provider data connection
        6. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            return False

        return verify_bluetooth_tethering_connection(self.log, self.provider, self.clients,
            toggle_tethering=False, toggle_bluetooth=False, toggle_data=True)


    @test_tracker_info(uuid="475b485a-1228-4f18-b9f2-593f96850165")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_bluetooth_tethering_toggle_tethering(self):
        """Bluetooth Tethering test: nsa 5G to Bluetooth Tethering

        1. DUT in nsa 5G mode, idle.
        2. DUT start Bluetooth Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB
        5. Toggle provider bluetooth tethering
        6. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Verify 4G Internet access failed.")
            return False

        return verify_bluetooth_tethering_connection(self.log, self.provider, self.clients,
            toggle_tethering=True, toggle_bluetooth=False, toggle_data=False)


    @test_tracker_info(uuid="07f8e523-b471-4156-b057-558123973a5b")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_bluetooth_tethering_rat_from_5g_nsa_to_4g(self):
        """Bluetooth Tethering test: nsa 5G to 4G Bluetooth Tethering

        1. DUT in nsa 5G mode, idle.
        2. DUT start bluetooth Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB
        5. Change provider RAT to 4G
        6. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Verify 5G Internet access failed.")
            return False

        return verify_bluetooth_tethering_connection(self.log, self.provider, self.clients,
            toggle_tethering=False,
            toggle_bluetooth=False,
            toggle_data=False,
            change_rat=RAT_4G)


    @test_tracker_info(uuid="93040a69-fa85-431f-ac9d-80091c6c8223")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_bluetooth_tethering_rat_from_5g_nsa_to_3g(self):
        """Bluetooth Tethering test: nsa5G to 3G Bluetooth Tethering

        1. DUT in nsa 5G mode, idle.
        2. DUT start bluetooth Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB
        5. Change provider RAT to 3G
        6. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Verify 5G Internet access failed.")
            return False

        return verify_bluetooth_tethering_connection(self.log, self.provider, self.clients,
            toggle_tethering=False,
            toggle_bluetooth=False,
            toggle_data=False,
            change_rat=RAT_3G)


    @test_tracker_info(uuid="6cc17fc7-13a0-4493-9673-920952a16fcc")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_bluetooth_tethering_rat_from_5g_nsa_to_2g(self):
        """Bluetooth Tethering test: nsa5G to 2G Bluetooth Tethering

        1. DUT in nsa 5G mode, idle.
        2. DUT start bluetooth Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verify Internet access on DUT and PhoneB
        5. Change provider RAT to 2G
        6. Verify Internet access on DUT and PhoneB

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Verify 5G Internet access failed.")
            return False

        return verify_bluetooth_tethering_connection(self.log, self.provider, self.clients,
            toggle_tethering=False,
            toggle_bluetooth=False,
            toggle_data=False,
            change_rat=RAT_2G)


    # Invalid Live Test. Can't rely on the result of this test with live network.
    # Network may decide not to change the RAT when data connection is active.
    @test_tracker_info(uuid="8bef3215-8218-4f7f-9a5f-954fa36ac5d8")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_wifi_tethering_from_5g_nsa_to_3g(self):
        """WiFi Tethering test: Change Cellular Data RAT generation from nsa 5G to 3G,
            during active WiFi Tethering.

        1. DUT in nsa 5G mode, idle.
        2. DUT start 2.4G WiFi Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verily Internet access on DUT and PhoneB
        5. Change DUT Cellular Data RAT generation from nsa5G to 3G.
        6. Verify both DUT and PhoneB have Internet access.

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Verify 5G Internet access failed.")
            return False
        try:
            if not wifi_tethering_setup_teardown(
                    self.log,
                    self.provider, [self.clients[0]],
                    ap_band=WIFI_CONFIG_APBAND_2G,
                    check_interval=10,
                    check_iteration=2,
                    do_cleanup=False):
                self.log.error("WiFi Tethering failed.")
                return False

            if not self.provider.droid.wifiIsApEnabled():
                self.provider.log.error("Provider WiFi tethering stopped.")
                return False

            self.log.info("Provider change RAT from nsa 5G to 3G.")
            if not ensure_network_generation(
                    self.log,
                    self.provider,
                    RAT_3G,
                    voice_or_data=NETWORK_SERVICE_DATA,
                    toggle_apm_after_setting=False):
                self.provider.log.error("Provider failed to reselect to 3G.")
                return False
            time.sleep(WAIT_TIME_DATA_STATUS_CHANGE_DURING_WIFI_TETHERING)
            if not verify_internet_connection(self.log, self.provider):
                self.provider.log.error("Data not available on Provider.")
                return False
            if not self.provider.droid.wifiIsApEnabled():
                self.provider.log.error("Provider WiFi tethering stopped.")
                return False
            if not tethering_check_internet_connection(
                    self.log, self.provider, [self.clients[0]], 10, 5):
                return False
        finally:
            if not wifi_tethering_cleanup(self.log, self.provider,
                                          self.clients):
                return False
        return True


    # Invalid Live Test. Can't rely on the result of this test with live network.
    # Network may decide not to change the RAT when data connection is active.
    @test_tracker_info(uuid="633f187d-3a8f-46dc-86de-f87b733a83ba")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_wifi_tethering_from_3g_to_5g_nsa(self):
        """WiFi Tethering test: Change Cellular Data RAT generation from 3G to nsa5G,
            during active WiFi Tethering.

        1. DUT in 3G mode, idle.
        2. DUT start 2.4G WiFi Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verily Internet access on DUT and PhoneB
        5. Change DUT Cellular Data RAT generation from 3G to nsa5G.
        6. Verify both DUT and PhoneB have Internet access.

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_3G):
            self.log.error("Verify 3G Internet access failed.")
            return False
        try:
            if not wifi_tethering_setup_teardown(
                    self.log,
                    self.provider, [self.clients[0]],
                    ap_band=WIFI_CONFIG_APBAND_2G,
                    check_interval=10,
                    check_iteration=2,
                    do_cleanup=False):
                self.log.error("WiFi Tethering failed.")
                return False

            if not self.provider.droid.wifiIsApEnabled():
                self.log.error("Provider WiFi tethering stopped.")
                return False

            self.log.info("Provider change RAT from 3G to 5G.")
            if not ensure_network_generation(
                    self.log,
                    self.provider,
                    RAT_4G,
                    voice_or_data=NETWORK_SERVICE_DATA,
                    toggle_apm_after_setting=False):
                self.log.error("Provider failed to reselect to LTE")
                return False
            if not provision_device_for_5g(self.log, self.provider):
                self.log.error("Provider failed to reselect to nsa 5G")
                return False
            time.sleep(WAIT_TIME_DATA_STATUS_CHANGE_DURING_WIFI_TETHERING)
            if not verify_internet_connection(self.log, self.provider):
                self.provider.log.error("Data not available on Provider.")
                return False
            if not self.provider.droid.wifiIsApEnabled():
                self.provider.log.error("Provider WiFi tethering stopped.")
                return False
            if not tethering_check_internet_connection(
                    self.log, self.provider, [self.clients[0]], 10, 5):
                return False
        finally:
            if not wifi_tethering_cleanup(self.log, self.provider, [self.clients[0]]):
                return False
        return True


    # Invalid Live Test. Can't rely on the result of this test with live network.
    # Network may decide not to change the RAT when data connection is active.
    @test_tracker_info(uuid="28e654a6-2318-4f36-a4f0-16214d8e004d")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_wifi_tethering_from_5g_nsa_to_4g(self):
        """WiFi Tethering test: Change Cellular Data RAT generation from nsa 5G to 4G,
            during active WiFi Tethering.

        1. DUT in nsa 5G mode, idle.
        2. DUT start 2.4G WiFi Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verily Internet access on DUT and PhoneB
        5. Change DUT Cellular Data RAT generation from nsa5G to LTE.
        6. Verify both DUT and PhoneB have Internet access.

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_5G):
            self.log.error("Verify 5G Internet access failed.")
            return False
        try:
            if not wifi_tethering_setup_teardown(
                    self.log,
                    self.provider, [self.clients[0]],
                    ap_band=WIFI_CONFIG_APBAND_2G,
                    check_interval=10,
                    check_iteration=2,
                    do_cleanup=False):
                self.log.error("WiFi Tethering failed.")
                return False

            if not self.provider.droid.wifiIsApEnabled():
                self.provider.log.error("Provider WiFi tethering stopped.")
                return False

            self.log.info("Provider change RAT from 5G to LTE.")
            if not ensure_network_generation(
                    self.log,
                    self.provider,
                    RAT_4G,
                    voice_or_data=NETWORK_SERVICE_DATA,
                    toggle_apm_after_setting=False):
                self.provider.log.error("Provider failed to reselect to 4G.")
                return False
            time.sleep(WAIT_TIME_DATA_STATUS_CHANGE_DURING_WIFI_TETHERING)
            if not verify_internet_connection(self.log, self.provider):
                self.provider.log.error("Data not available on Provider.")
                return False
            if not self.provider.droid.wifiIsApEnabled():
                self.provider.log.error("Provider WiFi tethering stopped.")
                return False
            if not tethering_check_internet_connection(
                    self.log, self.provider, [self.clients[0]], 10, 5):
                return False
        finally:
            if not wifi_tethering_cleanup(self.log, self.provider,
                                          self.clients):
                return False
        return True


    # Invalid Live Test. Can't rely on the result of this test with live network.
    # Network may decide not to change the RAT when data connection is active.
    @test_tracker_info(uuid="a8190c2a-a9ee-4673-b003-769691d1a575")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_wifi_tethering_from_4g_to_5g_nsa(self):
        """WiFi Tethering test: Change Cellular Data RAT generation from 4G to nsa5G,
            during active WiFi Tethering.

        1. DUT in 4G mode, idle.
        2. DUT start 2.4G WiFi Tethering
        3. PhoneB disable data, connect to DUT's softAP
        4. Verily Internet access on DUT and PhoneB
        5. Change DUT Cellular Data RAT generation from 4G to nsa5G.
        6. Verify both DUT and PhoneB have Internet access.

        Returns:
            True if success.
            False if failed.
        """
        if not test_setup_tethering(self.log, self.provider, self.clients, RAT_4G):
            self.log.error("Verify 4G Internet access failed.")
            return False
        try:
            if not wifi_tethering_setup_teardown(
                    self.log,
                    self.provider, [self.clients[0]],
                    ap_band=WIFI_CONFIG_APBAND_2G,
                    check_interval=10,
                    check_iteration=2,
                    do_cleanup=False):
                self.log.error("WiFi Tethering failed.")
                return False

            if not self.provider.droid.wifiIsApEnabled():
                self.log.error("Provider WiFi tethering stopped.")
                return False

            self.log.info("Provider change RAT from 4G to 5G.")
            if not ensure_network_generation(
                    self.log,
                    self.provider,
                    RAT_4G,
                    voice_or_data=NETWORK_SERVICE_DATA,
                    toggle_apm_after_setting=False):
                self.log.error("Provider failed to reselect to LTE")
                return False
            if not provision_device_for_5g(self.log, self.provider):
                self.log.error("Provider failed to reselect to nsa 5G")
                return False
            time.sleep(WAIT_TIME_DATA_STATUS_CHANGE_DURING_WIFI_TETHERING)
            if not verify_internet_connection(self.log, self.provider):
                self.provider.log.error("Data not available on Provider.")
                return False
            if not self.provider.droid.wifiIsApEnabled():
                self.provider.log.error("Provider WiFi tethering stopped.")
                return False
            if not tethering_check_internet_connection(
                    self.log, self.provider, [self.clients[0]], 10, 5):
                return False
        finally:
            if not wifi_tethering_cleanup(self.log, self.provider, [self.clients[0]]):
                return False
        return True


    @test_tracker_info(uuid="ac3ff18a-69e0-4a8a-bbfa-41fad7f05200")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_wifi_tethering_volte_call(self):
        """WiFi Tethering test: VoLTE call during WiFi tethering
        1. Start LTE to WiFi (2.4G) tethering.
        2. Verify tethering.
        3. Make outgoing VoLTE call on tethering provider.
        4. Verify tethering still works.
        5. Make incoming VoLTE call on tethering provider.
        6. Verify tethering still works.

        Returns:
            True if success.
            False if failed.
        """
        return test_tethering_wifi_and_voice_call(self.log, self.provider, self.clients,
            RAT_5G, phone_setup_volte, is_phone_in_call_volte)


    @test_tracker_info(uuid="8308bf40-7f1b-443f-bde6-19d9ff97e471")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_wifi_connect_disconnect(self):
        """Perform multiple connects and disconnects from WiFi and verify that
            data switches between WiFi and Cell.

        Steps:
        1. DUT Cellular Data is on nsa 5G. Reset Wifi on DUT
        2. Connect DUT to a WiFi AP
        3. Repeat steps 1-2, alternately disconnecting and disabling wifi

        Expected Results:
        1. Verify Data on Cell
        2. Verify Data on Wifi

        Returns:
            True if success.
            False if failed.
        """
        if not provision_device_for_5g(self.log, self.provider):
            return False

        return test_wifi_connect_disconnect(self.log, self.provider, self.wifi_network_ssid, self.wifi_network_pass)


    """ Tests End """
