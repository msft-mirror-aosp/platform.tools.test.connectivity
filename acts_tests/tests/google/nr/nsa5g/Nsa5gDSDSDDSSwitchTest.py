#!/usr/bin/env python3
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

import re
import time

from acts import asserts
from acts import signals
from acts.test_decorators import test_tracker_info
from acts.utils import rand_ascii_str
from acts_contrib.test_utils.tel.loggers.protos.telephony_metric_pb2 import TelephonyVoiceTestResult
from acts_contrib.test_utils.tel.loggers.telephony_metric_logger import TelephonyMetricLogger
from acts_contrib.test_utils.tel.tel_data_utils import reboot_test
from acts_contrib.test_utils.tel.tel_defines import CARRIER_FRE
from acts_contrib.test_utils.tel.tel_defines import GEN_3G
from acts_contrib.test_utils.tel.tel_defines import GEN_4G
from acts_contrib.test_utils.tel.tel_defines import GEN_5G
from acts_contrib.test_utils.tel.tel_defines import INVALID_SUB_ID
from acts_contrib.test_utils.tel.tel_defines import MAX_WAIT_TIME_SMS_RECEIVE
from acts_contrib.test_utils.tel.tel_defines import NETWORK_MODE_LTE_ONLY
from acts_contrib.test_utils.tel.tel_defines import NETWORK_SERVICE_DATA
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_ANDROID_STATE_SETTLING
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_IN_CALL
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_CELLULAR_PREFERRED
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_DISABLED
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_WIFI_ONLY
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_WIFI_PREFERRED
from acts_contrib.test_utils.tel.tel_defines import YOUTUBE_PACKAGE_NAME
from acts_contrib.test_utils.tel.tel_lookup_tables import network_preference_for_generation
from acts_contrib.test_utils.tel.tel_subscription_utils import get_default_data_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_from_slot_index
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_on_same_network_of_host_ad
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_0
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_1
from acts_contrib.test_utils.tel.tel_subscription_utils import set_message_subid
from acts_contrib.test_utils.tel.tel_subscription_utils import set_subid_for_data
from acts_contrib.test_utils.tel.tel_subscription_utils import set_voice_sub_id
from acts_contrib.test_utils.tel.tel_test_utils import check_is_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import ensure_network_generation_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import get_slot_index_from_subid
from acts_contrib.test_utils.tel.tel_test_utils import is_volte_available
from acts_contrib.test_utils.tel.tel_test_utils import is_volte_enabled
from acts_contrib.test_utils.tel.tel_test_utils import log_messaging_screen_shot
from acts_contrib.test_utils.tel.tel_test_utils import mms_send_receive_verify
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import set_preferred_network_mode_pref
from acts_contrib.test_utils.tel.tel_test_utils import set_wfc_mode_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import sms_send_receive_verify_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import start_youtube_video
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_test_utils import toggle_volte_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import toggle_wfc_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import verify_http_connection
from acts_contrib.test_utils.tel.tel_test_utils import verify_internet_connection
from acts_contrib.test_utils.tel.tel_test_utils import wait_for_cell_data_connection_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import wait_for_network_generation_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import wait_for_wfc_enabled
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import phone_idle_csfb_for_subscription
from acts_contrib.test_utils.tel.tel_voice_utils import phone_idle_volte_for_subscription
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_volte_for_subscription
from acts_contrib.test_utils.tel.tel_voice_utils import two_phone_call_msim_for_slot
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest

CallResult = TelephonyVoiceTestResult.CallResult.Value

class Nsa5gDSDSDDSSwitchTest(TelephonyBaseTest):
    def setup_class(self):
        TelephonyBaseTest.setup_class(self)
        self.message_lengths = (50, 160, 180)
        self.tel_logger = TelephonyMetricLogger.for_test_case()

    def setup_test(self):
        set_dds_on_slot_0(self.android_devices[0])

    def teardown_test(self):
        self.android_devices[0].force_stop_apk(YOUTUBE_PACKAGE_NAME)
        ensure_phones_idle(self.log, self.android_devices)

    def _get_network_preference_for_subscription(
            self, ad, sub_id, generation):
        """Get network preference string for given generation, e.g. NETWORK_MODE_NR_LTE_GSM_WCDMA.

        Args:
            ad: android device object.
            sub_id: subscription id.
            generation: network generation, e.g. GEN_2G, GEN_3G, GEN_4G, GEN_5G.

        Returns:
            network preference string for given generation.
        """
        network_preference = network_preference_for_generation(
            generation, ad.telephony["subscription"][sub_id]["operator"],
            ad.telephony["subscription"][sub_id]["phone_type"])
        if ad.telephony["subscription"][sub_id]["operator"] == CARRIER_FRE \
            and generation == GEN_4G:
            network_preference = NETWORK_MODE_LTE_ONLY
        ad.log.info("Network preference for %s is %s", generation,
                    network_preference)
        return network_preference

    def _set_dds_on_slot_with_network_generation_checking(
            self, log, ad, dds_slot, nw_gen):
        """Switch DDS and ensure ad's network is <network generation> for specified slot.

            Set DDS on specified slot.
            Wait for ad in expected network type.

        Args:
            log: log object.
            ad: android device object.
            dds_slot: the slot which be set to DDS.
            nw_gen: network generation, e.g. GEN_2G, GEN_3G, GEN_4G, GEN_5G.

        Returns:
            True if success, False if fail.
        """
        if dds_slot not in (0, 1):
            log.warning("dds_slot %d is invalid, must be 0 or 1.", dds_slot)
            return False

        if dds_slot:
            if not set_dds_on_slot_1(ad):
                return False
        else:
            if not set_dds_on_slot_0(ad):
                return False

        sub_id = get_subid_from_slot_index(log, ad, dds_slot)
        if not ensure_network_generation_for_subscription(
                log, ad, sub_id, nw_gen, voice_or_data=NETWORK_SERVICE_DATA):
            return False
        return True

    def _msim_message_test(
        self,
        ad_mo,
        ad_mt,
        mo_sub_id,
        mt_sub_id, msg="SMS",
        max_wait_time=MAX_WAIT_TIME_SMS_RECEIVE,
        expected_result=True):
        """Make MO/MT SMS/MMS at specific slot.

        Args:
            ad_mo: Android object of the device sending SMS/MMS
            ad_mt: Android object of the device receiving SMS/MMS
            mo_sub_id: Sub ID of MO device
            mt_sub_id: Sub ID of MT device
            max_wait_time: Max wait time before SMS/MMS is received.
            expected_result: True for successful sending/receiving and False on
                             the contrary

        Returns:
            True if the result matches expected_result and False on the
            contrary.
        """

        if msg == "SMS":
            for length in self.message_lengths:
                message_array = [rand_ascii_str(length)]
                if not sms_send_receive_verify_for_subscription(
                    self.log,
                    ad_mo,
                    ad_mt,
                    mo_sub_id,
                    mt_sub_id,
                    message_array,
                    max_wait_time):
                    ad_mo.log.warning(
                        "%s of length %s test failed", msg, length)
                    return False
                else:
                    ad_mo.log.info(
                        "%s of length %s test succeeded", msg, length)
            self.log.info("%s test of length %s characters succeeded.",
                msg, self.message_lengths)

        elif msg == "MMS":
            for length in self.message_lengths:
                message_array = [("Test Message", rand_ascii_str(length), None)]

                if not mms_send_receive_verify(
                    self.log,
                    ad_mo,
                    ad_mt,
                    message_array,
                    max_wait_time,
                    expected_result):
                    self.log.warning("%s of body length %s test failed",
                        msg, length)
                    return False
                else:
                    self.log.info(
                        "%s of body length %s test succeeded", msg, length)
            self.log.info("%s test of body lengths %s succeeded",
                          msg, self.message_lengths)
        return True

    def _test_dds_switch_during_data_transfer(
        self,
        nw_rat=["5g_volte", "5g_volte"],
        call_slot=0,
        call_direction=None,
        call_or_sms_or_mms="call",
        streaming=True,
        is_airplane_mode=False,
        wfc_mode=[WFC_MODE_CELLULAR_PREFERRED, WFC_MODE_CELLULAR_PREFERRED]):
        """Switch DDS and make voice call (VoLTE/WFC/CS call)/SMS/MMS together
        with Youtube playing after each DDS switch at specific slot in specific
        RAT.

        Test step:
            1. Get sub ID of each slot of the primary device.
            2. Set up phones in desired RAT.
            3. Switch DDS to slot 0.
            4. Check HTTP connection after DDS switch.
            5. Play Youtube.
            6. Make voice call (VoLTE/WFC/CS call)/SMS/MMS
            7. Switch DDS to slot 1 and repeat step 4-6.
            8. Switch DDS to slot 0 again and repeat step 4-6.

        Args:
            nw_rat: RAT for both slots of the primary device
            call_slot: Slot for making voice call
            call_direction: "mo" or "mt" or None to stoping making call.
            call_or_sms_or_mms: Voice call or SMS or MMS
            streaming: True for playing Youtube after DDS switch and False on the contrary.
            is_airplane_mode: True of False for WFC setup
            wfc_mode: Cellular preferred or Wi-Fi preferred.

        Returns:
            True or False
        """
        ad = self.android_devices[0]
        slot_0_subid = get_subid_from_slot_index(self.log, ad, 0)
        slot_1_subid = get_subid_from_slot_index(self.log, ad, 1)
        nw_gen = []
        for slot in range(len(nw_rat)):
            if "5g" in nw_rat[slot].lower():
                nw_gen.append(GEN_5G)
            elif nw_rat[slot].lower() == "3g":
                nw_gen.append(GEN_3G)
            else:
                nw_gen.append(GEN_4G)

        if slot_0_subid == INVALID_SUB_ID or slot_1_subid == INVALID_SUB_ID:
            ad.log.error("Not all slots have valid sub ID.")
            raise signals.TestFailure("Failed",
                extras={"fail_reason": "Not all slots have valid sub ID"})

        ad.log.info(
            "Step 0: Set up phone in desired RAT (slot 0: %s, slot 1: %s)",
            nw_rat[0], nw_rat[1])

        if not phone_setup_on_rat(
            self.log,
            ad,
            nw_rat[0],
            slot_0_subid,
            is_airplane_mode,
            wfc_mode[0],
            self.wifi_network_ssid,
            self.wifi_network_pass):
            self.log.error("Phone Failed to Set Up Properly.")
            self.tel_logger.set_result(CallResult("CALL_SETUP_FAILURE"))
            raise signals.TestFailure("Failed",
                extras={"fail_reason": "Phone Failed to Set Up Properly."})

        slot_1_network_preference = (
            self._get_network_preference_for_subscription(
                ad, slot_1_subid, nw_gen[1]))
        if not set_preferred_network_mode_pref(self.log, ad, slot_1_subid,
                slot_1_network_preference):
            self.log.error("Phone Failed to Set Up Properly.")
            self.tel_logger.set_result(CallResult("CALL_SETUP_FAILURE"))
            raise signals.TestFailure("Failed",
                extras={"fail_reason": "Phone Failed to Set Up Properly."})
        if not wait_for_network_generation_for_subscription(
            self.log,
            ad,
            slot_1_subid,
            GEN_4G,
            voice_or_data=NETWORK_SERVICE_DATA):
            return False

        if "volte" in nw_rat[1]:
            toggle_volte_for_subscription(self.log, ad, slot_1_subid, True)
            if not phone_idle_volte_for_subscription(self.log, ad, slot_1_subid):
                return False
        elif "csfb" in nw_rat[1]:
            toggle_volte_for_subscription(self.log, ad, slot_1_subid, False)
            if not phone_idle_csfb_for_subscription(self.log, ad, slot_1_subid):
                return False
            if is_volte_available(self.log, ad, slot_1_subid):
                ad.log.info("IMS is registered for sub ID %s, "
                    "IsVolteCallingAvailable is True", slot_1_subid)
                return False

        is_slot0_in_call = is_phone_in_call_on_rat(
            self.log, ad, nw_rat[0], True)
        is_slot1_in_call = is_phone_in_call_on_rat(
            self.log, ad, nw_rat[1], True)

        for attempt in range(3):
            if attempt != 0:
                ad.log.info("Repeat step 1 to 4.")

            ad.log.info("Step 1: Switch DDS.")
            if attempt % 2 == 0:
                self._set_dds_on_slot_with_network_generation_checking(
                    self.log, ad, 0, nw_gen[0])
            else:
                self._set_dds_on_slot_with_network_generation_checking(
                    self.log, ad, 1, nw_gen[1])

            ad.log.info("Step 2: Check HTTP connection after DDS switch.")
            if not verify_http_connection(self.log, ad):
                ad.log.error("Failed to verify http connection.")
                return False
            else:
                ad.log.info("Verify http connection successfully.")

            if streaming:
                ad.log.info("Step 3: Start Youtube streaming.")
                if not start_youtube_video(ad):
                    ad.log.warning("Fail to bring up youtube video")
                time.sleep(10)
            else:
                ad.log.info("Step 3: Skip Youtube streaming.")

            if not call_direction:
                return True
            else:
                expected_result = True
                if call_direction == "mo":
                    ad_mo = self.android_devices[0]
                    ad_mt = self.android_devices[1]
                    mo_sub_id = get_subid_from_slot_index(self.log, ad, call_slot)
                    if call_or_sms_or_mms == "call":
                        set_voice_sub_id(ad_mo, mo_sub_id)
                        _, mt_sub_id, _ = get_subid_on_same_network_of_host_ad(
                            self.android_devices)

                        if call_slot == 0:
                            is_mo_in_call = is_slot0_in_call
                        elif call_slot == 1:
                            is_mo_in_call = is_slot1_in_call
                        is_mt_in_call = None

                    elif call_or_sms_or_mms == "sms":
                        set_message_subid(ad_mo, mo_sub_id)
                        _, mt_sub_id, _ = get_subid_on_same_network_of_host_ad(
                            self.android_devices, type="sms")
                        set_message_subid(ad_mt, mt_sub_id)

                    elif call_or_sms_or_mms == "mms":
                        current_data_sub_id = get_default_data_sub_id(ad_mo)
                        if mo_sub_id != current_data_sub_id:
                            ad_mo.log.warning(
                                "Current data sub ID (%s) does not match"
                                " message sub ID (%s). MMS should NOT be sent.",
                                current_data_sub_id, mo_sub_id)
                            expected_result = False
                        set_message_subid(ad_mo, mo_sub_id)
                        _, mt_sub_id, _ = get_subid_on_same_network_of_host_ad(
                            self.android_devices, type="sms")
                        set_message_subid(ad_mt, mt_sub_id)
                        set_subid_for_data(ad_mt, mt_sub_id)
                        ad_mt.droid.telephonyToggleDataConnection(True)

                elif call_direction == "mt":
                    ad_mo = self.android_devices[1]
                    ad_mt = self.android_devices[0]
                    mt_sub_id = get_subid_from_slot_index(self.log, ad, call_slot)
                    if call_or_sms_or_mms == "call":
                        set_voice_sub_id(ad_mt, mt_sub_id)
                        _, mo_sub_id, _ = get_subid_on_same_network_of_host_ad(
                            self.android_devices)

                        if call_slot == 0:
                            is_mt_in_call = is_slot0_in_call
                        elif call_slot == 1:
                            is_mt_in_call = is_slot1_in_call
                        is_mo_in_call = None

                    elif call_or_sms_or_mms == "sms":
                        set_message_subid(ad_mt, mt_sub_id)
                        _, mo_sub_id, _ = get_subid_on_same_network_of_host_ad(
                            self.android_devices, type="sms")
                        set_message_subid(ad_mo, mo_sub_id)

                    elif call_or_sms_or_mms == "mms":
                        current_data_sub_id = get_default_data_sub_id(ad_mt)
                        if mt_sub_id != current_data_sub_id:
                            ad_mt.log.warning(
                                "Current data sub ID (%s) does not match"
                                " message sub ID (%s). MMS should NOT be"
                                " received.", current_data_sub_id, mt_sub_id)
                            expected_result = False
                        set_message_subid(ad_mt, mt_sub_id)
                        _, mo_sub_id, _ = get_subid_on_same_network_of_host_ad(
                            self.android_devices, type="sms")
                        set_message_subid(ad_mo, mo_sub_id)
                        set_subid_for_data(ad_mo, mo_sub_id)
                        ad_mo.droid.telephonyToggleDataConnection(True)

                if call_or_sms_or_mms == "call":
                    self.log.info("Step 4: Make voice call.")
                    mo_slot = get_slot_index_from_subid(
                        self.log, ad_mo, mo_sub_id)
                    mt_slot = get_slot_index_from_subid(
                        self.log, ad_mt, mt_sub_id)
                    result = two_phone_call_msim_for_slot(
                        self.log,
                        ad_mo,
                        mo_slot,
                        None,
                        is_mo_in_call,
                        ad_mt,
                        mt_slot,
                        None,
                        is_mt_in_call)
                    self.tel_logger.set_result(result.result_value)

                    if not result:
                        self.log.error(
                            "Failed to make MO call from %s slot %s to %s"
                            " slot %s", ad_mo.serial, mo_slot, ad_mt.serial,
                            mt_slot)
                        raise signals.TestFailure("Failed",
                            extras={"fail_reason": str(result.result_value)})
                else:
                    self.log.info("Step 4: Send %s.", call_or_sms_or_mms)
                    if call_or_sms_or_mms == "sms":
                        result = self._msim_message_test(
                            ad_mo,
                            ad_mt,
                            mo_sub_id,
                            mt_sub_id,
                            msg=call_or_sms_or_mms.upper())
                    elif call_or_sms_or_mms == "mms":
                        result = self._msim_message_test(
                            ad_mo,
                            ad_mt,
                            mo_sub_id,
                            mt_sub_id,
                            msg=call_or_sms_or_mms.upper(),
                            expected_result=expected_result)
                    if not result:
                        log_messaging_screen_shot(
                            ad_mo, test_name="%s_tx" % call_or_sms_or_mms)
                        log_messaging_screen_shot(
                            ad_mt, test_name="%s_rx" % call_or_sms_or_mms)

                        return False
            if streaming:
                ad.force_stop_apk(YOUTUBE_PACKAGE_NAME)
        return True

    @test_tracker_info(uuid="727a75ef-7277-42fe-8a4b-7b2debe666d9")
    @TelephonyBaseTest.tel_test_wrap
    def test_dds_switch_youtube_psim_5g_nsa_volte_esim_5g_nsa_volte(self):
        return self._test_dds_switch_during_data_transfer(
            nw_rat=["5g_volte", "5g_volte"])

    @test_tracker_info(uuid="4ef4626a-11b3-4a09-ac98-2e3d94e54bf7")
    @TelephonyBaseTest.tel_test_wrap
    def test_dds_switch_youtube_and_voice_mo_psim_5g_nsa_volte_esim_5g_nsa_volte(self):
        return self._test_dds_switch_during_data_transfer(
            nw_rat=["5g_volte", "5g_volte"],
            call_slot=0,
            call_direction="mo")

    @test_tracker_info(uuid="ef3bc49f-e94f-432b-bb51-4b6008359313")
    @TelephonyBaseTest.tel_test_wrap
    def test_dds_switch_youtube_and_voice_mt_psim_5g_nsa_volte_esim_5g_nsa_volte(self):
        return self._test_dds_switch_during_data_transfer(
            nw_rat=["5g_volte", "5g_volte"],
            call_slot=0,
            call_direction="mt")

    @test_tracker_info(uuid="6d913c58-dde5-453d-b9a9-30e76cdac554")
    @TelephonyBaseTest.tel_test_wrap
    def test_dds_switch_youtube_and_voice_mo_esim_5g_nsa_volte_psim_5g_nsa_volte(self):
        return self._test_dds_switch_during_data_transfer(
            nw_rat=["5g_volte", "5g_volte"],
            call_slot=1,
            call_direction="mo")

    @test_tracker_info(uuid="df91d2ce-ef5e-4d38-a642-6470ade625c6")
    @TelephonyBaseTest.tel_test_wrap
    def test_dds_switch_youtube_and_voice_mt_esim_5g_nsa_volte_psim_5g_nsa_volte(self):
        return self._test_dds_switch_during_data_transfer(
            nw_rat=["5g_volte", "5g_volte"],
            call_slot=1,
            call_direction="mt")

    @test_tracker_info(uuid="4ba86f3c-1de6-4888-a2e5-a5e6079c3886")
    @TelephonyBaseTest.tel_test_wrap
    def test_dds_switch_youtube_and_voice_mo_psim_5g_nsa_csfb_esim_5g_nsa_csfb(self):
        return self._test_dds_switch_during_data_transfer(
            nw_rat=["5g_csfb", "5g_csfb"],
            call_slot=0,
            call_direction="mo")

    @test_tracker_info(uuid="aa426eb2-dc7b-4ffe-aaa2-a3204251c131")
    @TelephonyBaseTest.tel_test_wrap
    def test_dds_switch_youtube_and_voice_mt_psim_5g_nsa_csfb_esim_5g_nsa_csfb(self):
        return self._test_dds_switch_during_data_transfer(
            nw_rat=["5g_csfb", "5g_csfb"],
            call_slot=0,
            call_direction="mt")

    @test_tracker_info(uuid="854634e8-7a2a-4d14-8269-8f4f463f8f56")
    @TelephonyBaseTest.tel_test_wrap
    def test_dds_switch_youtube_and_voice_mo_esim_5g_nsa_csfb_psim_5g_nsa_csfb(self):
        return self._test_dds_switch_during_data_transfer(
            nw_rat=["5g_csfb", "5g_csfb"],
            call_slot=1,
            call_direction="mo")

    @test_tracker_info(uuid="02478b9e-6bf6-4148-bbc4-0cbdf59f1625")
    @TelephonyBaseTest.tel_test_wrap
    def test_dds_switch_youtube_and_voice_mt_esim_5g_nsa_csfb_psim_5g_nsa_csfb(self):
        return self._test_dds_switch_during_data_transfer(
            nw_rat=["5g_csfb", "5g_csfb"],
            call_slot=1,
            call_direction="mt")