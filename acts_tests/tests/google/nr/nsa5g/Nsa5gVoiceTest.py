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
    Test Script for 5G Voice scenarios
"""

import time

from acts.test_decorators import test_tracker_info
from acts.utils import adb_shell_ping
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_IN_CALL_FOR_IMS
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_IN_CALL
from acts_contrib.test_utils.tel.tel_defines import CALL_STATE_ACTIVE
from acts_contrib.test_utils.tel.tel_defines import CALL_STATE_HOLDING
from acts_contrib.test_utils.tel.tel_defines import DIRECTION_MOBILE_ORIGINATED
from acts_contrib.test_utils.tel.tel_defines import DIRECTION_MOBILE_TERMINATED
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_ANDROID_STATE_SETTLING
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_WIFI_PREFERRED
from acts_contrib.test_utils.tel.tel_defines import GEN_5G
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_test_utils import call_setup_teardown
from acts_contrib.test_utils.tel.tel_test_utils import hangup_call
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import num_active_calls
from acts_contrib.test_utils.tel.tel_test_utils import verify_incall_state
from acts_contrib.test_utils.tel.tel_test_utils import verify_internet_connection
from acts_contrib.test_utils.tel.tel_test_utils import start_youtube_video
from acts_contrib.test_utils.tel.tel_test_utils import wait_for_cell_data_connection
from acts_contrib.test_utils.tel.tel_test_utils import active_file_download_task
from acts_contrib.test_utils.tel.tel_test_utils import run_multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import wait_for_state
from acts_contrib.test_utils.tel.tel_test_utils import is_phone_in_call_active
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_volte
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_volte
from acts_contrib.test_utils.tel.tel_voice_utils import two_phone_call_short_seq
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_voice_3g
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_3g
from acts_contrib.test_utils.tel.tel_voice_utils import phone_idle_iwlan
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_iwlan
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_iwlan
from acts_contrib.test_utils.tel.tel_5g_utils import set_preferred_mode_for_5g
from acts_contrib.test_utils.tel.tel_5g_utils import provision_both_devices_for_5g
from acts_contrib.test_utils.tel.tel_5g_utils import provision_both_devices_for_volte
from acts_contrib.test_utils.tel.tel_5g_utils import verify_5g_attach_for_both_devices
from acts_contrib.test_utils.tel.tel_5g_utils import is_current_network_5g_nsa
from acts_contrib.test_utils.tel.tel_5g_utils import wifi_cell_switching_for_5g_nsa


class Nsa5gVoiceTest(TelephonyBaseTest):
    def setup_class(self):
        super().setup_class()
        self.number_of_devices = 2
        self.message_lengths = (50, 160, 180)

    def setup_test(self):
        TelephonyBaseTest.setup_test(self)

    def teardown_test(self):
        ensure_phones_idle(self.log, self.android_devices)


    def _hold_unhold_test(self, ads):
        """ Test hold/unhold functionality.

        PhoneA is in call with PhoneB. The call on PhoneA is active.
        Get call list on PhoneA.
        Hold call_id on PhoneA.
        Check call_id state.
        Unhold call_id on PhoneA.
        Check call_id state.

        Args:
            ads: List of android objects.
                This list should contain 2 android objects.
                ads[0] is the ad to do hold/unhold operation.

        Returns:
            True if pass; False if fail.
        """
        call_list = ads[0].droid.telecomCallGetCallIds()
        ads[0].log.info("Calls in PhoneA %s", call_list)
        if num_active_calls(ads[0].log, ads[0]) != 1:
            return False
        call_id = call_list[0]
        if ads[0].droid.telecomCallGetCallState(call_id) != CALL_STATE_ACTIVE:
            ads[0].log.error("call_id:%s, state:%s, expected: STATE_ACTIVE",
                             call_id,
                             ads[0].droid.telecomCallGetCallState(call_id))
            return False
        ads[0].log.info("hold call_id %s on PhoneA", call_id)
        ads[0].droid.telecomCallHold(call_id)
        time.sleep(WAIT_TIME_IN_CALL)
        if ads[0].droid.telecomCallGetCallState(call_id) != CALL_STATE_HOLDING:
            ads[0].log.error("call_id:%s, state:%s, expected: STATE_HOLDING",
                             call_id,
                             ads[0].droid.telecomCallGetCallState(call_id))
            return False
        ads[0].log.info("unhold call_id %s on PhoneA", call_id)
        ads[0].droid.telecomCallUnhold(call_id)
        time.sleep(WAIT_TIME_IN_CALL)
        if ads[0].droid.telecomCallGetCallState(call_id) != CALL_STATE_ACTIVE:
            ads[0].log.error("call_id:%s, state:%s, expected: STATE_ACTIVE",
                             call_id,
                             ads[0].droid.telecomCallGetCallState(call_id))
            return False
        if not verify_incall_state(self.log, [ads[0], ads[1]], True):
            self.log.error("caller/callee dropped call.")
            return False
        return True


    def _test_call_setup_in_active_data_transfer_5g_nsa(
            self,
            new_gen=None,
            call_direction=DIRECTION_MOBILE_ORIGINATED,
            allow_data_transfer_interruption=False):
        """Test call can be established during active data connection in 5G NSA.

        Turn off airplane mode, disable WiFi, enable Cellular Data.
        Make sure phone in 5G NSA.
        Starting downloading file from Internet.
        Initiate a voice call. Verify call can be established.
        Hangup Voice Call, verify file is downloaded successfully.
        Note: file download will be suspended when call is initiated if voice
              is using voice channel and voice channel and data channel are
              on different RATs.

        Returns:
            True if success.
            False if failed.
        """
        ads = self.android_devices

        def _call_setup_teardown(log, ad_caller, ad_callee, ad_hangup,
                                 caller_verifier, callee_verifier,
                                 wait_time_in_call):
            #wait time for active data transfer
            time.sleep(5)
            return call_setup_teardown(log, ad_caller, ad_callee, ad_hangup,
                                       caller_verifier, callee_verifier,
                                       wait_time_in_call)

        # Mode Pref
        set_preferred_mode_for_5g(ads[0])

        # Attach nsa5g
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5G NSA before call.")
            return False

        if new_gen:
            ads[0].droid.telephonyToggleDataConnection(True)
            if not wait_for_cell_data_connection(self.log, ads[0], True):
                ads[0].log.error("Data connection is not on cell")
                return False

        if not verify_internet_connection(self.log, ads[0]):
            ads[0].log.error("Internet connection is not available")
            return False

        if call_direction == DIRECTION_MOBILE_ORIGINATED:
            ad_caller = ads[0]
            ad_callee = ads[1]
        else:
            ad_caller = ads[1]
            ad_callee = ads[0]
        ad_download = ads[0]

        start_youtube_video(ad_download)
        call_task = (_call_setup_teardown, (self.log, ad_caller, ad_callee,
                                            ad_caller, None, None, 30))
        download_task = active_file_download_task(self.log, ad_download, file_name="10MB")
        results = run_multithread_func(self.log, [download_task, call_task])
        if wait_for_state(ad_download.droid.audioIsMusicActive, True, 15, 1):
            ad_download.log.info("After call hangup, audio is back to music")
        else:
            ad_download.log.warning(
                "After call hang up, audio is not back to music")
        ad_download.force_stop_apk("com.google.android.youtube")
        if not results[1]:
            self.log.error("Call setup failed in active data transfer.")
            return False
        if results[0]:
            ad_download.log.info("Data transfer succeeded.")
            return True
        elif not allow_data_transfer_interruption:
            ad_download.log.error(
                "Data transfer failed with parallel phone call.")
            return False
        else:
            ad_download.log.info("Retry data connection after call hung up")
            if not verify_internet_connection(self.log, ad_download):
                ad_download.log.error("Internet connection is not available")
                return False
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5G NSA after call.")
            return False
        return True

    def _test_call_setup_in_active_youtube_video_5g_nsa(
            self,
            new_gen=None,
            call_direction=DIRECTION_MOBILE_ORIGINATED,
            allow_data_transfer_interruption=False):
        """Test call can be established during active data connection on 5G NSA.

        Setup phoneA on 5G NSA.
        Make sure phoneA on 5G NSA
        Starting playing youtube video.
        Initiate a voice call. Verify call can be established.
        Make sure phoneA on 5G NSA

        Returns:
            True if success.
            False if failed.
        """
        ads = self.android_devices
        # Mode Pref
        set_preferred_mode_for_5g(ads[0])

        # Attach 5g
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5G NSA before call.")
            return False

        if new_gen:
            ads[0].droid.telephonyToggleDataConnection(True)
            if not wait_for_cell_data_connection(self.log, ads[0], True):
                ads[0].log.error("Data connection is not on cell")
                return False

        if not verify_internet_connection(self.log, ads[0]):
            ads[0].log.error("Internet connection is not available")
            return False

        if call_direction == DIRECTION_MOBILE_ORIGINATED:
            ad_caller = ads[0]
            ad_callee = ads[1]
        else:
            ad_caller = ads[1]
            ad_callee = ads[0]
        ad_download = ads[0]

        if not start_youtube_video(ad_download):
            ad_download.log.warning("Fail to bring up youtube video")

        if not call_setup_teardown(self.log, ad_caller, ad_callee, ad_caller,
                                   None, None, 30):
            ad_download.log.error("Call setup failed in active youtube video")
            result = False
        else:
            ad_download.log.info("Call setup succeed in active youtube video")
            result = True

        if wait_for_state(ad_download.droid.audioIsMusicActive, True, 15, 1):
            ad_download.log.info("After call hangup, audio is back to music")
        else:
            ad_download.log.warning(
                "After call hang up, audio is not back to music")
        ad_download.force_stop_apk("com.google.android.youtube")
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5G NSA after call.")
            result = False
        return result

    def _call_epdg_to_epdg_wfc_5g_nsa(self,
                                      ads,
                                      apm_mode,
                                      wfc_mode,
                                      wifi_ssid,
                                      wifi_pwd):
        """ Test epdg<->epdg call functionality on 5G NSA.

        Set PhoneA/PhoneB on 5G NSA
        Make sure PhoneA/PhoneB on 5G NSA before testing
        Make Sure PhoneA is set to make epdg call.
        Make Sure PhoneB is set to make epdg call.
        Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneA.
        Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneB.
        Make sure PhoneA/PhoneB on 5G NSA after testing

        Args:
            ads: list of android objects, this list should have two ad.
            apm_mode: phones' airplane mode.
                if True, phones are in airplane mode during test.
                if False, phones are not in airplane mode during test.
            wfc_mode: phones' wfc mode.
                Valid mode includes: WFC_MODE_WIFI_ONLY, WFC_MODE_CELLULAR_PREFERRED,
                WFC_MODE_WIFI_PREFERRED, WFC_MODE_DISABLED.
            wifi_ssid: WiFi ssid to connect during test.
            wifi_pwd: WiFi password.

        Returns:
            True if pass; False if fail.
        """
        DEFAULT_PING_DURATION = 120  # in seconds

        # if apm_mode is true, turn off apm first before setting network
        # preferred mode to 5G NSA.
        if apm_mode:
            # Turn off airplane mode
            self.log.info("Turn off APM mode before starting testing.")
            tasks = [(toggle_airplane_mode, (self.log, ads[0], False)),
                     (toggle_airplane_mode, (self.log, ads[1], False))]
            if not multithread_func(self.log, tasks):
                self.log.error("Failed to turn off airplane mode")
                return False

        if not provision_both_devices_for_5g(self.log, ads):
            return False

        if not verify_5g_attach_for_both_devices(self.log, ads):
            self.log.error("Phone not attached on 5G NSA before epdg call.")
            return False

        tasks = [(phone_setup_iwlan, (self.log, ads[0], apm_mode, wfc_mode,
                                      wifi_ssid, wifi_pwd)),
                 (phone_setup_iwlan, (self.log, ads[1], apm_mode, wfc_mode,
                                      wifi_ssid, wifi_pwd))]
        if not multithread_func(self.log, tasks):
            self.log.error("Phone Failed to Set Up Properly.")
            return False

        time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

        ad_ping = ads[0]

        call_task = (two_phone_call_short_seq,
                     (self.log, ads[0], phone_idle_iwlan,
                      is_phone_in_call_iwlan, ads[1], phone_idle_iwlan,
                      is_phone_in_call_iwlan, None, WAIT_TIME_IN_CALL_FOR_IMS))
        ping_task = (adb_shell_ping, (ad_ping, DEFAULT_PING_DURATION))

        results = run_multithread_func(self.log, [ping_task, call_task])

        time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

        if not verify_5g_attach_for_both_devices(self.log, ads):
            self.log.error("Phone not attached on 5G NSA after epdg call.")
            return False

        if not results[1]:
            self.log.error("Call setup failed in active ICMP transfer.")
        if results[0]:
            self.log.info("ICMP transfer succeeded with parallel phone call.")
        else:
            self.log.error("ICMP transfer failed with parallel phone call.")
        return all(results)

    """ Tests Begin """

    @test_tracker_info(uuid="1bef3da1-4608-4b0e-8b78-f3f7be0115d5")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_volte_to_volte(self):
        """ 5g nsa volte to volte call test

        1. Make sure PhoneA is in nsa5g mode (with volte).
        2. Make sure PhoneB is in nsa5g mode (with volte).
        3. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneA.
        4. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneB.
        5. Verify both PhoneA and PhoneB gets attached back to nsa5g

        Raises:
            TestFailure if not success.
        """
        ads = self.android_devices
        if not provision_both_devices_for_volte(self.log, ads):
            return False

        if not provision_both_devices_for_5g(self.log, ads):
            return False

        # VoLTE calls
        result = two_phone_call_short_seq(
            self.log, ads[0], None, is_phone_in_call_volte, ads[1],
            None, is_phone_in_call_volte, None,
            WAIT_TIME_IN_CALL_FOR_IMS)
        if not result:
            self.log.error("Failure is volte call during 5g nsa")
            return False

        if not verify_5g_attach_for_both_devices(self.log, ads):
            return False

        self.log.info("PASS - volte test over 5g nsa validated")
        return True

    @test_tracker_info(uuid="3df252a4-308a-49c3-8e37-08e9c4e8efef")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_volte_to_3g(self):
        """ 5g nsa volte to 3g call test

        1. Make sure PhoneA is in nsa5g mode (with volte).
        2. Make sure PhoneB is in 3g mode.
        3. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneA.
        4. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneB.
        5. Verify both PhoneA and PhoneB gets attached back to nsa5g

        Raises:
            TestFailure if not success.
        """
        ads = self.android_devices

        # LTE attach
        tasks = [(phone_setup_volte, (self.log, ads[0])),
                 (phone_setup_voice_3g, (self.log, ads[1]))]
        if not multithread_func(self.log, tasks):
            self.log.error("Phone failed to set up in volte/3g")
            return False

        # Mode Pref
        set_preferred_mode_for_5g(ads[0])

        # Attach nsa5g
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5g nsa before call.")
            return False

        # VoLTE to 3G
        result = two_phone_call_short_seq(
            self.log, ads[0], None, is_phone_in_call_volte, ads[1],
            None, is_phone_in_call_3g, None,
            WAIT_TIME_IN_CALL_FOR_IMS)
        if not result:
            self.log.error("Failure is volte to 3g call during 5g nsa")
            return False

        # Attach nsa5g
        if not is_current_network_5g_nsa(ads[0]):
            ads[0].log.error("Phone not attached on 5g nsa after call end.")
            return False

        self.log.info("PASS - VoLTE to 3g over 5g nsa validated")
        return True


    @test_tracker_info(uuid="3a8147d6-c136-42cb-92ca-2023b8eed85e")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_volte_mo_hold_unhold(self):
        """ 5g nsa volte mo hold unhold test

        1. Make sure PhoneA is in nsa 5g (with volte)
        2. Make sure PhoneB is in nsa 5g (with volte)
        3. Call from PhoneA to PhoneB, accept on PhoneB
        4. Make sure PhoneA/B are in call
        5. Hold and unhold on PhoneA
        6. Verify both PhoneA and PhoneB gets attached back to nsa5g

        Raises:
            TestFailure if not success.
        """
        ads = self.android_devices
        if not provision_both_devices_for_volte(self.log, ads):
            return False

        if not provision_both_devices_for_5g(self.log, ads):
            return False

        ads[0].droid.telecomCallClearCallList()
        if num_active_calls(self.log, ads[0]) != 0:
            ads[0].log.error("call list is not empty")
            return False

        self.log.info("begin hold/unhold test")
        if not call_setup_teardown(
                self.log,
                ads[0],
                ads[1],
                ad_hangup=None,
                verify_caller_func=is_phone_in_call_volte,
                verify_callee_func=None):
            return False

        if not self._hold_unhold_test(ads):
            self.log.error("hold/unhold test fail.")
            return False

        if not hangup_call(self.log, ads[0]):
            self.log.error("call hangup failed")
            return False

        if not verify_5g_attach_for_both_devices(self.log, ads):
            return False
        return True

    @test_tracker_info(uuid="1825f9d9-dcf1-4407-922d-3f218d5b8932")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_volte_mt_hold_unhold(self):
        """ 5g nsa volte mt hold unhold test

        1. Make sure PhoneA is in nsa 5g (with volte)
        2. Make sure PhoneB is in nsa 5g (with volte)
        3. Call from PhoneB to PhoneA, accept on PhoneA
        4. Make sure PhoneA/B are in call
        5. Hold and unhold on PhoneA
        6. Verify both PhoneA and PhoneB gets attached back to nsa5g

        Raises:
            TestFailure if not success.
        """
        ads = self.android_devices
        if not provision_both_devices_for_volte(self.log, ads):
            return False

        if not provision_both_devices_for_5g(self.log, ads):
            return False

        ads[0].droid.telecomCallClearCallList()
        if num_active_calls(self.log, ads[0]) != 0:
            ads[0].log.error("call list is not empty.")
            return False

        self.log.info("begin mt call hold/unhold Test.")
        if not call_setup_teardown(
                self.log,
                ads[1],
                ads[0],
                ad_hangup=None,
                verify_caller_func=None,
                verify_callee_func=is_phone_in_call_volte):
            return False

        if not self._hold_unhold_test(ads):
            self.log.error("hold/unhold test fail.")
            return False

        if not hangup_call(self.log, ads[0]):
            self.log.error("call hangup failed")
            return False

        if not verify_5g_attach_for_both_devices(self.log, ads):
            return False
        return True


    @test_tracker_info(uuid="c082a9b0-fb66-4d3a-9fdd-1ce5710624be")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mo_volte_in_active_data_transfer(self):
        """Test call can be established during active data connection in 5G NSA.

        Turn off airplane mode, disable WiFi, enable Cellular Data.
        Make sure phone in 5G NSA.
        Starting downloading file from Internet.
        Initiate a MO voice call. Verify call can be established.
        Hangup Voice Call, verify file is downloaded successfully.
        Note: file download will be suspended when call is initiated if voice
              is using voice channel and voice channel and data channel are
              on different RATs.

        Returns:
            True if success.
            False if failed.
        """
        ads = self.android_devices
        if not phone_setup_volte(self.log, ads[0]):
            ads[0].log.error("failed to setup volte")
            return False
        return self._test_call_setup_in_active_data_transfer_5g_nsa(
            GEN_5G,
            DIRECTION_MOBILE_ORIGINATED)


    @test_tracker_info(uuid="aaa98e51-0bde-472a-abc3-5dc180f56a08")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mt_volte_in_active_data_transfer(self):
        """Test call can be established during active data connection in 5G NSA.

        Turn off airplane mode, disable WiFi, enable Cellular Data.
        Make sure phone in 5G NSA.
        Starting downloading file from Internet.
        Initiate a MT voice call. Verify call can be established.
        Hangup Voice Call, verify file is downloaded successfully.
        Note: file download will be suspended when call is initiated if voice
              is using voice channel and voice channel and data channel are
              on different RATs.

        Returns:
            True if success.
            False if failed.
        """
        ads = self.android_devices
        if not phone_setup_volte(self.log, ads[0]):
            ads[0].log.error("failed to setup volte")
            return False
        return self._test_call_setup_in_active_data_transfer_5g_nsa(
            GEN_5G,
            DIRECTION_MOBILE_TERMINATED)


    @test_tracker_info(uuid="3a607dee-7e92-4567-8ca0-05099590b773")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_volte_in_call_wifi_toggling(self):
        """ Test data connection network switching during VoLTE call in 5G NSA.

        1. Make Sure PhoneA in VoLTE.
        2. Make Sure PhoneB in VoLTE.
        3. Make sure Phones are in 5G NSA
        4. Call from PhoneA to PhoneB.
        5. Toggling Wifi connection in call.
        6. Verify call is active.
        7. Hung up the call on PhoneA
        8. Make sure Phones are in 5G NSA

        Returns:
            True if pass; False if fail.
        """
        ads = self.android_devices
        result = True
        if not provision_both_devices_for_volte(self.log, ads):
            return False

        time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

        if not provision_both_devices_for_5g(self.log, ads):
            return False

        if not verify_5g_attach_for_both_devices(self.log, ads):
            self.log.error("Phone not attached on 5G NSA before call.")
            return False

        if not call_setup_teardown(self.log, ads[0], ads[1], None, None, None,
                                   5):
            self.log.error("Call setup failed")
            return False
        else:
            self.log.info("Call setup succeed")

        if not wifi_cell_switching_for_5g_nsa(self.log, ads[0], self.wifi_network_ssid,
                                              self.wifi_network_pass):
            ads[0].log.error("Failed to do WIFI and Cell switch in call")
            result = False

        if not is_phone_in_call_active(ads[0]):
            return False
        else:
            if not ads[0].droid.telecomCallGetAudioState():
                ads[0].log.error("Audio is not on call")
                result = False
            else:
                ads[0].log.info("Audio is on call")
            hangup_call(self.log, ads[0])

            time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

            if not verify_5g_attach_for_both_devices(self.log, ads):
                self.log.error("Phone not attached on 5G NSA after call.")
                return False
            return result


    @test_tracker_info(uuid="96b7d8c9-d32a-4abf-8326-6b060d116ac2")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_epdg_to_epdg_wfc_wifi_preferred(self):
        """ WiFi Preferred, WiFi calling to WiFi Calling test on 5G NSA

        1. Setup PhoneA WFC mode: WIFI_PREFERRED, APM off.
        2. Setup PhoneB WFC mode: WIFI_PREFERRED, APM off .
        3. Set PhoneA/PhoneB on 5G NSA
        4. Make sure PhoneA/PhoneB on 5G NSA before testing
        5. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneA.
        6. Call from PhoneA to PhoneB, accept on PhoneB, hang up on PhoneB.
        7. Make sure PhoneA/PhoneB on 5G NSA after testing

        Returns:
            True if pass; False if fail.
        """
        return self._call_epdg_to_epdg_wfc_5g_nsa(
            self.android_devices, False, WFC_MODE_WIFI_PREFERRED,
            self.wifi_network_ssid, self.wifi_network_pass)


    @test_tracker_info(uuid="29fa7f44-8d6a-4948-8178-33c9a9aab334")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mo_volte_in_active_youtube(self):
        """Test call can be established during active youtube video on 5G NSA.

        1. Enable VoLTE on PhoneA.
        2. Set up PhoneA on 5G NSA.
        3. Make sure phoneA is on 5G NSA.
        4. Starting an youtube video.
        5. Initiate a MO voice call. Verify call can be established.
        6. Make sure phoneA is on 5G NSA.

        Returns:
            True if success.
            False if failed.
        """
        if not phone_setup_volte(self.log, self.android_devices[0]):
            self.android_devices[0].log.error("Failed to setup VoLTE")
            return False
        return self._test_call_setup_in_active_youtube_video_5g_nsa(
            GEN_5G,
            DIRECTION_MOBILE_ORIGINATED)

    @test_tracker_info(uuid="4e138477-3536-48bd-ab8a-7fb7c228b3e6")
    @TelephonyBaseTest.tel_test_wrap
    def test_5g_nsa_call_mt_volte_in_active_youtube(self):
        """Test call can be established during active youtube video on 5G NSA.

        1. Enable VoLTE on PhoneA.
        2. Set up PhoneA on 5G NSA.
        3. Make sure phoneA is on 5G NSA.
        4. Starting an youtube video.
        5. Initiate a MT voice call. Verify call can be established.
        6. Make sure phoneA is on 5G NSA.

        Returns:
            True if success.
            False if failed.
        """
        if not phone_setup_volte(self.log, self.android_devices[0]):
            self.android_devices[0].log.error("Failed to setup VoLTE")
            return False
        return self._test_call_setup_in_active_youtube_video_5g_nsa(
            GEN_5G,
            DIRECTION_MOBILE_TERMINATED)

    """ Tests End """
