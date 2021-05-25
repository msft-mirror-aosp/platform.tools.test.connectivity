#!/usr/bin/env python3
#
#   Copyright 2021 - Google
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

import time

from acts import asserts
from acts import signals
from acts.test_decorators import test_tracker_info
from acts.utils import rand_ascii_str
from acts_contrib.test_utils.tel.loggers.protos.telephony_metric_pb2 import TelephonyVoiceTestResult
from acts_contrib.test_utils.tel.loggers.telephony_metric_logger import TelephonyMetricLogger
from acts_contrib.test_utils.tel.tel_defines import CARRIER_FRE
from acts_contrib.test_utils.tel.tel_defines import GEN_3G
from acts_contrib.test_utils.tel.tel_defines import GEN_4G
from acts_contrib.test_utils.tel.tel_defines import GEN_5G
from acts_contrib.test_utils.tel.tel_defines import INVALID_SUB_ID
from acts_contrib.test_utils.tel.tel_defines import MAX_WAIT_TIME_SMS_RECEIVE
from acts_contrib.test_utils.tel.tel_defines import NETWORK_MODE_LTE_ONLY
from acts_contrib.test_utils.tel.tel_defines import NETWORK_SERVICE_DATA
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_ANDROID_STATE_SETTLING
from acts_contrib.test_utils.tel.tel_lookup_tables import network_preference_for_generation
from acts_contrib.test_utils.tel.tel_subscription_utils import get_default_data_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_incoming_voice_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_outgoing_message_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_from_slot_index
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_on_same_network_of_host_ad
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_0
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_1
from acts_contrib.test_utils.tel.tel_subscription_utils import set_message_subid
from acts_contrib.test_utils.tel.tel_subscription_utils import set_subid_for_data
from acts_contrib.test_utils.tel.tel_subscription_utils import set_voice_sub_id
from acts_contrib.test_utils.tel.tel_test_utils import ensure_phones_idle
from acts_contrib.test_utils.tel.tel_test_utils import get_slot_index_from_subid
from acts_contrib.test_utils.tel.tel_test_utils import is_volte_available
from acts_contrib.test_utils.tel.tel_test_utils import log_messaging_screen_shot
from acts_contrib.test_utils.tel.tel_test_utils import mms_send_receive_verify
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import set_preferred_network_mode_pref
from acts_contrib.test_utils.tel.tel_test_utils import sms_in_collision_send_receive_verify_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import sms_rx_power_off_multiple_send_receive_verify_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import sms_send_receive_verify_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import toggle_volte_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import verify_http_connection
from acts_contrib.test_utils.tel.tel_test_utils import voice_call_in_collision_with_mt_sms_msim
from acts_contrib.test_utils.tel.tel_test_utils import wait_for_network_generation_for_subscription
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import phone_idle_csfb_for_subscription
from acts_contrib.test_utils.tel.tel_voice_utils import phone_idle_volte_for_subscription
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_voice_general_for_subscription
from acts_contrib.test_utils.tel.TelephonyBaseTest import TelephonyBaseTest

CallResult = TelephonyVoiceTestResult.CallResult.Value

class Nsa5gDsdsMessageTest(TelephonyBaseTest):
    def setup_class(self):
        TelephonyBaseTest.setup_class(self)
        self.message_lengths = (50, 160, 180)
        self.tel_logger = TelephonyMetricLogger.for_test_case()

    def teardown_test(self):
        ensure_phones_idle(self.log, self.android_devices)

    def _phone_setup_on_rat_for_non_dds_slot(
        self,
        ad,
        non_dds_slot,
        rat='5g_volte'):
        """Pre-setting for DSDS device on non-DDS slot before test begin.

            Set up ad in desired RAT for non-DDS slot and check the specific network generation.

        Args:
            ad: android device object.
            non_dds_slot: The slot which is non-DDS slot.
            rat: RAT for non-DDS of given ad.

        Returns:
            True or False.
        """
        sub_id = get_subid_from_slot_index(self.log, ad, non_dds_slot)
        if "5g" in rat.lower():
            generation = GEN_5G
        elif rat.lower() == "3g":
            generation = GEN_3G
        else:
            generation = GEN_4G

        if generation == GEN_5G:
            check_gen = GEN_4G
        else:
            check_gen = generation

        network_preference = network_preference_for_generation(
            generation, ad.telephony["subscription"][sub_id]["operator"],
            ad.telephony["subscription"][sub_id]["phone_type"])
        if ad.telephony["subscription"][sub_id]["operator"] == CARRIER_FRE \
            and generation == GEN_4G:
            network_preference = NETWORK_MODE_LTE_ONLY
        ad.log.info("Network preference for %s is %s", generation,
            network_preference)

        if not set_preferred_network_mode_pref(self.log, ad, sub_id,
            network_preference):
            return False
        if not wait_for_network_generation_for_subscription(
            self.log,
            ad,
            sub_id,
            check_gen,
            voice_or_data=NETWORK_SERVICE_DATA):
            return False

        if "volte" in rat.lower():
            toggle_volte_for_subscription(self.log, ad, sub_id, True)
            if not phone_idle_volte_for_subscription(self.log, ad, sub_id):
                return False
        elif "csfb" in rat.lower():
            toggle_volte_for_subscription(self.log, ad, sub_id, False)
            if not phone_idle_csfb_for_subscription(self.log, ad, sub_id):
                return False
            if is_volte_available(self.log, ad, sub_id):
                ad.log.info("IMS is registered for sub ID %s, "
                    "IsVolteCallingAvailable is True", sub_id)
                return False
        return True


    def _pre_setup_dds_and_rat(
        self,
        ad,
        dds_slot,
        nw_rat=["5g_volte", "5g_volte"],
        is_airplane_mode=False,
        wfc_mode=None):
        """Pre-setting on DSDS device before test begin.

            Switch DDS to given DDS slot.
            Check HTTP connection after DDS switch.
            Set up ad in desired RAT for both slots and check the network generation.

        Args:
            ad: android device object.
            dds_slot: The slot which be set to DDS.
            nw_rat: RAT for both slots of given ad.
            is_airplane_mode: The argument for phone_setup_on_rat().
                True to turn on airplane mode. False to turn off airplane mode.
            wfc_mode: WFC mode to set to.

        Returns:
            True or False.
        """
        subid = []
        for slot in range(len(nw_rat)):
            subid.append(get_subid_from_slot_index(self.log, ad, slot))
        if INVALID_SUB_ID in subid:
            ad.log.error("Not all slots have valid sub ID.")
            raise signals.TestFailure("Failed",
                extras={"fail_reason": "Not all slots have valid sub ID"})

        ad.log.info("Pre-Condition: 1. Switch DDS.")
        if not set_dds_on_slot(ad, dds_slot):
            return False
        ad.log.info("Pre-Condition: 2. Check HTTP connection after DDS switch.")
        if not verify_http_connection(self.log, ad):
            ad.log.error("Failed to verify http connection.")
            return False
        else:
            ad.log.info("Verify http connection successfully.")
        ad.log.info(
            "Pre-Condition: 3. Set up phone in desired RAT "
            "(slot 0: %s, slot 1: %s)", nw_rat[0], nw_rat[1])
        if not phone_setup_on_rat(
            self.log,
            ad,
            nw_rat[dds_slot],
            subid[dds_slot],
            is_airplane_mode,
            wfc_mode,
            self.wifi_network_ssid,
            self.wifi_network_pass):
            return False
        if not self._phone_setup_on_rat_for_non_dds_slot(
            ad, 1-dds_slot, nw_rat[1-dds_slot]):
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

    def _test_msim_message(
            self,
            mo_slot,
            mt_slot,
            dds_slot,
            msg="SMS",
            mo_rat=["", ""],
            mt_rat=["", ""],
            direction="mo",
            expected_result=True):
        """Make MO/MT SMS/MMS at specific slot in specific RAT with DDS at
        specific slot.

        Test step:
        1. Get sub IDs of specific slots of both MO and MT devices.
        2. Switch DDS to specific slot.
        3. Check HTTP connection after DDS switch.
        4. Set up phones in desired RAT.
        5. Send SMS/MMS.

        Args:
            mo_slot: Slot sending MO SMS (0 or 1)
            mt_slot: Slot receiving MT SMS (0 or 1)
            dds_slot: Preferred data slot
            mo_rat: RAT for both slots of MO device
            mt_rat: RAT for both slots of MT device
            direction: "mo" or "mt"
            expected_result: True of False

        Returns:
            TestFailure if failed.
        """
        ads = self.android_devices

        if direction == "mo":
            ad_mo = ads[0]
            ad_mt = ads[1]
        else:
            ad_mo = ads[1]
            ad_mt = ads[0]

        if mo_slot is not None:
            mo_sub_id = get_subid_from_slot_index(self.log, ad_mo, mo_slot)
            if mo_sub_id == INVALID_SUB_ID:
                ad_mo.log.warning("Failed to get sub ID at slot %s.", mo_slot)
                return False
            set_message_subid(ad_mo, mo_sub_id)
        else:
            _, mo_sub_id, _ = get_subid_on_same_network_of_host_ad(
                ads, type="sms")
            if mo_sub_id == INVALID_SUB_ID:
                ad_mo.log.warning("Failed to get sub ID at slot %s.", mo_slot)
                return False
            mo_slot = "auto"
            set_message_subid(ad_mo, mo_sub_id)
            if msg == "MMS":
                set_subid_for_data(ad_mo, mo_sub_id)
                ad_mo.droid.telephonyToggleDataConnection(True)
        ad_mo.log.info("Sub ID for outgoing %s at slot %s: %s", msg, mo_slot,
            get_outgoing_message_sub_id(ad_mo))

        if mt_slot is not None:
            mt_sub_id = get_subid_from_slot_index(self.log, ad_mt, mt_slot)
            if mt_sub_id == INVALID_SUB_ID:
                ad_mt.log.warning("Failed to get sub ID at slot %s.", mt_slot)
                return False
            set_message_subid(ad_mt, mt_sub_id)
        else:
            _, mt_sub_id, _ = get_subid_on_same_network_of_host_ad(
                ads, type="sms")
            if mt_sub_id == INVALID_SUB_ID:
                ad_mt.log.warning("Failed to get sub ID at slot %s.", mt_slot)
                return False
            mt_slot = "auto"
            set_message_subid(ad_mt, mt_sub_id)
            if msg == "MMS":
                set_subid_for_data(ad_mt, mt_sub_id)
                ad_mt.droid.telephonyToggleDataConnection(True)
        ad_mt.log.info("Sub ID for incoming %s at slot %s: %s", msg, mt_slot,
                       get_outgoing_message_sub_id(ad_mt))

        mo_phone_setup_func_argv = (self.log, ad_mo, mo_sub_id)
        mt_phone_setup_func_argv = (self.log, ad_mt, mt_sub_id)

        if direction == "mo":
            phone_setup_on_rat(self.log, ad_mt, 'general', sub_id_type='sms')
            mt_phone_setup_func = phone_setup_voice_general_for_subscription
            mo_phone_setup_func_argv = (ad_mo, dds_slot, mo_rat)
            mo_phone_setup_func = self._pre_setup_dds_and_rat
        else:
            phone_setup_on_rat(self.log, ad_mo, 'general', sub_id_type='sms')
            mo_phone_setup_func = phone_setup_voice_general_for_subscription
            mt_phone_setup_func_argv = (ad_mt, dds_slot, mt_rat)
            mt_phone_setup_func = self._pre_setup_dds_and_rat

        self.log.info("Pre-Condition start.")
        tasks = [(mo_phone_setup_func, mo_phone_setup_func_argv),
                 (mt_phone_setup_func, mt_phone_setup_func_argv)]
        if not multithread_func(self.log, tasks):
            self.log.error("Phone Failed to Set Up Properly.")
            raise signals.TestFailure("Failed",
                extras={"fail_reason": "Phone Failed to Set Up Properly."})

        time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)
        self.log.info("Step 1: Send %s.", msg)

        if msg == "MMS":
            for ad, current_data_sub_id, current_msg_sub_id in [
                [ ads[0],
                  get_default_data_sub_id(ads[0]),
                  get_outgoing_message_sub_id(ads[0]) ],
                [ ads[1],
                  get_default_data_sub_id(ads[1]),
                  get_outgoing_message_sub_id(ads[1]) ]]:
                if current_data_sub_id != current_msg_sub_id:
                    ad.log.warning(
                        "Current data sub ID (%s) does not match message"
                        " sub ID (%s). MMS should NOT be sent.",
                        current_data_sub_id,
                        current_msg_sub_id)
                    expected_result = False

        result = self._msim_message_test(ad_mo, ad_mt, mo_sub_id, mt_sub_id,
            msg=msg, expected_result=expected_result)

        if not result:
            log_messaging_screen_shot(ad_mo, test_name="%s_tx" % msg)
            log_messaging_screen_shot(ad_mt, test_name="%s_rx" % msg)

        return result

    @test_tracker_info(uuid="123a50bc-f0a0-4129-9377-cc63c76d5727")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_0(self):
        return self._test_msim_message(
            0, None, 0, mo_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="5dcf76bc-369f-4d47-b3ec-318559a95843")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_0(self):
        return self._test_msim_message(
            None, 0, 0, mt_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="dd4a9fb5-b0fe-492b-ad24-61e022d13a22")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_0(self):
        return self._test_msim_message(
            1, None, 0, mo_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="09100a8f-b7ed-41a0-9f04-e716115cabb8")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_0(self):
        return self._test_msim_message(
            None, 1, 0, mt_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="245a6148-cd45-4b82-bf4c-5679ebe15e29")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_1(self):
        return self._test_msim_message(
            0, None, 1, mo_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="5a93d377-d9bc-477c-bfab-2496064e3522")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_5g_nsa_volte_esim_5g_nsa_volte_dds_1(self):
        return self._test_msim_message(
            None, 0, 1, mt_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="b5971c57-bbe9-4e87-a6f2-9953fa770a15")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_1(self):
        return self._test_msim_message(
            1, None, 1, mo_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="142b11d4-b593-4a09-8fc6-35e310739244")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_5g_nsa_volte_psim_5g_nsa_volte_dds_1(self):
        return self._test_msim_message(
            None, 1, 1, mt_rat=["5g_volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="87759475-0208-4d9b-b5b9-814fdb97f09c")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_5g_nsa_volte_esim_4g_volte_dds_0(self):
        return self._test_msim_message(
            0, None, 0, mo_rat=["5g_volte", "volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="2f14e81d-330f-4cdd-837c-1168185ffec4")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_5g_nsa_volte_esim_4g_volte_dds_0(self):
        return self._test_msim_message(
            None, 0, 0, mt_rat=["5g_volte", "volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="9cc45474-1fca-4008-8499-87829d6516ea")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_4g_volte_psim_5g_nsa_volte_dds_0(self):
        return self._test_msim_message(
            1, None, 0, mo_rat=["5g_volte", "volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="341786de-5b23-438a-a91b-97cf420ef5fd")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_4g_volte_psim_5g_nsa_volte_dds_0(self):
        return self._test_msim_message(
            None, 1, 0, mt_rat=["5g_volte", "volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="51d5e05d-66e7-4369-91e0-6cdc573d9a59")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_esim_5g_nsa_volte_psim_4g_volte_dds_1(self):
        return self._test_msim_message(
            1, None, 1, mo_rat=["volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="38271a0f-2efb-4991-9f24-6da9f003ddd4")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_esim_5g_nsa_volte_psim_4g_volte_dds_1(self):
        return self._test_msim_message(
            None, 1, 1, mt_rat=["volte", "5g_volte"], msg="SMS", direction="mt")

    @test_tracker_info(uuid="183cda35-45aa-485d-b3d4-975d78f7d361")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mo_psim_4g_volte_esim_5g_nsa_volte_dds_1(self):
        return self._test_msim_message(
            0, None, 1, mo_rat=["volte", "5g_volte"], msg="SMS", direction="mo")

    @test_tracker_info(uuid="d9cb69ce-c462-4fd4-b716-bfb1fd2ed86a")
    @TelephonyBaseTest.tel_test_wrap
    def test_msim_sms_mt_psim_4g_volte_esim_5g_nsa_volte_dds_1(self):
        return self._test_msim_message(
            None, 0, 1, mt_rat=["volte", "5g_volte"], msg="SMS", direction="mt")
