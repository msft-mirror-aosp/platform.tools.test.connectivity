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

import re
import time

from acts import signals
from acts.utils import rand_ascii_str
from acts_contrib.test_utils.tel.loggers.protos.telephony_metric_pb2 import TelephonyVoiceTestResult
from acts_contrib.test_utils.tel.loggers.telephony_metric_logger import TelephonyMetricLogger
from acts_contrib.test_utils.tel.tel_defines import INVALID_SUB_ID
from acts_contrib.test_utils.tel.tel_defines import MAX_WAIT_TIME_SMS_RECEIVE
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_ANDROID_STATE_SETTLING
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_CELLULAR_PREFERRED
from acts_contrib.test_utils.tel.tel_subscription_utils import get_default_data_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_incoming_voice_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_outgoing_message_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_outgoing_voice_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_from_slot_index
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_on_same_network_of_host_ad
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_0
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_1
from acts_contrib.test_utils.tel.tel_subscription_utils import set_message_subid
from acts_contrib.test_utils.tel.tel_subscription_utils import set_subid_for_data
from acts_contrib.test_utils.tel.tel_subscription_utils import set_voice_sub_id
from acts_contrib.test_utils.tel.tel_test_utils import call_setup_teardown
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import erase_call_forwarding_by_mmi
from acts_contrib.test_utils.tel.tel_test_utils import get_operator_name
from acts_contrib.test_utils.tel.tel_test_utils import get_slot_index_from_subid
from acts_contrib.test_utils.tel.tel_test_utils import hangup_call
from acts_contrib.test_utils.tel.tel_test_utils import initiate_call
from acts_contrib.test_utils.tel.tel_test_utils import log_messaging_screen_shot
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import mms_send_receive_verify
from acts_contrib.test_utils.tel.tel_test_utils import num_active_calls
from acts_contrib.test_utils.tel.tel_test_utils import set_call_forwarding_by_mmi
from acts_contrib.test_utils.tel.tel_test_utils import set_call_waiting
from acts_contrib.test_utils.tel.tel_test_utils import set_wfc_mode_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import sms_send_receive_verify_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_test_utils import toggle_wfc_for_subscription
from acts_contrib.test_utils.tel.tel_test_utils import verify_incall_state
from acts_contrib.test_utils.tel.tel_test_utils import verify_http_connection
from acts_contrib.test_utils.tel.tel_test_utils import wait_and_reject_call_for_subscription
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_voice_general
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import swap_calls
from acts_contrib.test_utils.tel.tel_voice_utils import three_phone_call_forwarding_short_seq
from acts_contrib.test_utils.tel.tel_voice_utils import three_phone_call_waiting_short_seq
from acts_contrib.test_utils.tel.tel_voice_utils import two_phone_call_msim_for_slot
from acts_contrib.test_utils.tel.tel_voice_conf_utils import _test_ims_conference_merge_drop_second_call_from_participant
from acts_contrib.test_utils.tel.tel_voice_conf_utils import _test_wcdma_conference_merge_drop
from acts_contrib.test_utils.tel.tel_voice_conf_utils import _three_phone_call_mo_add_mt

CallResult = TelephonyVoiceTestResult.CallResult.Value
tel_logger = TelephonyMetricLogger.for_test_case()

def dsds_voice_call_test(
        log,
        ads,
        mo_slot,
        mt_slot,
        dds,
        mo_rat=["", ""],
        mt_rat=["", ""],
        call_direction="mo"):
    """Make MO/MT voice call at specific slot in specific RAT with DDS at
    specific slot.

    Test step:
    1. Get sub IDs of specific slots of both MO and MT devices.
    2. Switch DDS to specific slot.
    3. Check HTTP connection after DDS switch.
    4. Set up phones in desired RAT.
    5. Make voice call.

    Args:
        log: logger object
        ads: list of android devices
        mo_slot: Slot making MO call (0 or 1)
        mt_slot: Slot receiving MT call (0 or 1)
        dds: Preferred data slot
        mo_rat: RAT for both slots of MO device
        mt_rat: RAT for both slots of MT device
        call_direction: "mo" or "mt"

    Returns:
        TestFailure if failed.
    """
    if call_direction == "mo":
        ad_mo = ads[0]
        ad_mt = ads[1]
    else:
        ad_mo = ads[1]
        ad_mt = ads[0]

    if mo_slot is not None:
        mo_sub_id = get_subid_from_slot_index(log, ad_mo, mo_slot)
        if mo_sub_id == INVALID_SUB_ID:
            ad_mo.log.warning("Failed to get sub ID ar slot %s.", mo_slot)
            return False
        mo_other_sub_id = get_subid_from_slot_index(
            log, ad_mo, 1-mo_slot)
        set_voice_sub_id(ad_mo, mo_sub_id)
    else:
        _, mo_sub_id, _ = get_subid_on_same_network_of_host_ad(ads)
        if mo_sub_id == INVALID_SUB_ID:
            ad_mo.log.warning("Failed to get sub ID ar slot %s.", mo_slot)
            return False
        mo_slot = "auto"
        set_voice_sub_id(ad_mo, mo_sub_id)
    ad_mo.log.info("Sub ID for outgoing call at slot %s: %s",
        mo_slot, get_outgoing_voice_sub_id(ad_mo))

    if mt_slot is not None:
        mt_sub_id = get_subid_from_slot_index(log, ad_mt, mt_slot)
        if mt_sub_id == INVALID_SUB_ID:
            ad_mt.log.warning("Failed to get sub ID at slot %s.", mt_slot)
            return False
        mt_other_sub_id = get_subid_from_slot_index(
            log, ad_mt, 1-mt_slot)
        set_voice_sub_id(ad_mt, mt_sub_id)
    else:
        _, mt_sub_id, _ = get_subid_on_same_network_of_host_ad(ads)
        if mt_sub_id == INVALID_SUB_ID:
            ad_mt.log.warning("Failed to get sub ID at slot %s.", mt_slot)
            return False
        mt_slot = "auto"
        set_voice_sub_id(ad_mt, mt_sub_id)
    ad_mt.log.info("Sub ID for incoming call at slot %s: %s", mt_slot,
        get_incoming_voice_sub_id(ad_mt))

    log.info("Step 1: Switch DDS.")
    if not set_dds_on_slot(ads[0], dds):
        log.error(
            "Failed to set DDS at slot %s on %s",(dds, ads[0].serial))
        return False

    log.info("Step 2: Check HTTP connection after DDS switch.")
    if not verify_http_connection(log, ads[0]):
        log.error("Failed to verify http connection.")
        return False
    else:
        log.info("Verify http connection successfully.")

    if mo_slot == 0 or mo_slot == 1:
        phone_setup_on_rat(log, ad_mo, mo_rat[1-mo_slot], mo_other_sub_id)
        mo_phone_setup_func_argv = (log, ad_mo, mo_rat[mo_slot], mo_sub_id)
        is_mo_in_call = is_phone_in_call_on_rat(
            log, ad_mo, mo_rat[mo_slot], only_return_fn=True)
    else:
        mo_phone_setup_func_argv = (log, ad_mo, 'general')
        is_mo_in_call = is_phone_in_call_on_rat(
            log, ad_mo, 'general', only_return_fn=True)

    if mt_slot == 0 or mt_slot == 1:
        phone_setup_on_rat(log, ad_mt, mt_rat[1-mt_slot], mt_other_sub_id)
        mt_phone_setup_func_argv = (log, ad_mt, mt_rat[mt_slot], mt_sub_id)
        is_mt_in_call = is_phone_in_call_on_rat(
            log, ad_mt, mt_rat[mt_slot], only_return_fn=True)
    else:
        mt_phone_setup_func_argv = (log, ad_mt, 'general')
        is_mt_in_call = is_phone_in_call_on_rat(
            log, ad_mt, 'general', only_return_fn=True)

    log.info("Step 3: Set up phones in desired RAT.")
    tasks = [(phone_setup_on_rat, mo_phone_setup_func_argv),
                (phone_setup_on_rat, mt_phone_setup_func_argv)]
    if not multithread_func(log, tasks):
        log.error("Phone Failed to Set Up Properly.")
        tel_logger.set_result(CallResult("CALL_SETUP_FAILURE"))
        raise signals.TestFailure("Failed",
            extras={"fail_reason": "Phone Failed to Set Up Properly."})

    log.info("Step 4: Make voice call.")
    result = two_phone_call_msim_for_slot(
        log,
        ad_mo,
        get_slot_index_from_subid(log, ad_mo, mo_sub_id),
        None,
        is_mo_in_call,
        ad_mt,
        get_slot_index_from_subid(log, ad_mt, mt_sub_id),
        None,
        is_mt_in_call)

    tel_logger.set_result(result.result_value)

    if not result:
        log.error(
            "Failed to make MO call from %s slot %s to %s slot %s",
                ad_mo.serial, mo_slot, ad_mt.serial, mt_slot)
        raise signals.TestFailure("Failed",
            extras={"fail_reason": str(result.result_value)})

def dsds_message_test(
        log,
        ads,
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
    if direction == "mo":
        ad_mo = ads[0]
        ad_mt = ads[1]
    else:
        ad_mo = ads[1]
        ad_mt = ads[0]

    if mo_slot is not None:
        mo_sub_id = get_subid_from_slot_index(log, ad_mo, mo_slot)
        if mo_sub_id == INVALID_SUB_ID:
            ad_mo.log.warning("Failed to get sub ID at slot %s.", mo_slot)
            return False
        mo_other_sub_id = get_subid_from_slot_index(
            log, ad_mo, 1-mo_slot)
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
        mt_sub_id = get_subid_from_slot_index(log, ad_mt, mt_slot)
        if mt_sub_id == INVALID_SUB_ID:
            ad_mt.log.warning("Failed to get sub ID at slot %s.", mt_slot)
            return False
        mt_other_sub_id = get_subid_from_slot_index(log, ad_mt, 1-mt_slot)
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

    log.info("Step 1: Switch DDS.")
    if not set_dds_on_slot(ads[0], dds_slot):
        log.error(
            "Failed to set DDS at slot %s on %s",(dds_slot, ads[0].serial))
        return False

    log.info("Step 2: Check HTTP connection after DDS switch.")
    if not verify_http_connection(log, ads[0]):
        log.error("Failed to verify http connection.")
        return False
    else:
        log.info("Verify http connection successfully.")

    if mo_slot == 0 or mo_slot == 1:
        phone_setup_on_rat(log, ad_mo, mo_rat[1-mo_slot], mo_other_sub_id)
        mo_phone_setup_func_argv = (log, ad_mo, mo_rat[mo_slot], mo_sub_id)
    else:
        mo_phone_setup_func_argv = (log, ad_mo, 'general', mo_sub_id)

    if mt_slot == 0 or mt_slot == 1:
        phone_setup_on_rat(log, ad_mt, mt_rat[1-mt_slot], mt_other_sub_id)
        mt_phone_setup_func_argv = (log, ad_mt, mt_rat[mt_slot], mt_sub_id)
    else:
        mt_phone_setup_func_argv = (log, ad_mt, 'general', mt_sub_id)

    log.info("Step 3: Set up phones in desired RAT.")
    tasks = [(phone_setup_on_rat, mo_phone_setup_func_argv),
                (phone_setup_on_rat, mt_phone_setup_func_argv)]
    if not multithread_func(log, tasks):
        log.error("Phone Failed to Set Up Properly.")
        return False

    time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)
    log.info("Step 4: Send %s.", msg)

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

    result = msim_message_test(log, ad_mo, ad_mt, mo_sub_id, mt_sub_id,
        msg=msg, expected_result=expected_result)

    if not result:
        log_messaging_screen_shot(ad_mo, test_name="%s_tx" % msg)
        log_messaging_screen_shot(ad_mt, test_name="%s_rx" % msg)

    return result

def erase_call_forwarding(log, ad):
    slot0_sub_id = get_subid_from_slot_index(log, ad, 0)
    slot1_sub_id = get_subid_from_slot_index(log, ad, 1)
    current_voice_sub_id = get_incoming_voice_sub_id(ad)
    for sub_id in (slot0_sub_id, slot1_sub_id):
        set_voice_sub_id(ad, sub_id)
        get_operator_name(log, ad, sub_id)
        erase_call_forwarding_by_mmi(log, ad)
    set_voice_sub_id(ad, current_voice_sub_id)

def three_way_calling_mo_and_mt_with_hangup_once(
    log,
    ads,
    phone_setups,
    verify_funcs,
    reject_once=False):
    """Use 3 phones to make MO call and MT call.

    Call from PhoneA to PhoneB, accept on PhoneB.
    Call from PhoneC to PhoneA, accept on PhoneA.

    Args:
        ads: list of ad object.
            The list should have three objects.
        phone_setups: list of phone setup functions.
            The list should have three objects.
        verify_funcs: list of phone call verify functions.
            The list should have three objects.

    Returns:
        If success, return 'call_AB' id in PhoneA.
        if fail, return None.
    """

    class _CallException(Exception):
        pass

    try:
        verify_func_a, verify_func_b, verify_func_c = verify_funcs
        tasks = []
        for ad, setup_func in zip(ads, phone_setups):
            if setup_func is not None:
                tasks.append((setup_func, (log, ad, get_incoming_voice_sub_id(ad))))
        if tasks != [] and not multithread_func(log, tasks):
            log.error("Phone Failed to Set Up Properly.")
            raise _CallException("Setup failed.")
        for ad in ads:
            ad.droid.telecomCallClearCallList()
            if num_active_calls(log, ad) != 0:
                ad.log.error("Phone Call List is not empty.")
                raise _CallException("Clear call list failed.")

        log.info("Step1: Call From PhoneA to PhoneB.")
        if not call_setup_teardown(
                log,
                ads[0],
                ads[1],
                ad_hangup=None,
                verify_caller_func=verify_func_a,
                verify_callee_func=verify_func_b):
            raise _CallException("PhoneA call PhoneB failed.")

        calls = ads[0].droid.telecomCallGetCallIds()
        ads[0].log.info("Calls in PhoneA %s", calls)
        if num_active_calls(log, ads[0]) != 1:
            raise _CallException("Call list verify failed.")
        call_ab_id = calls[0]

        log.info("Step2: Call From PhoneC to PhoneA.")
        if reject_once:
            log.info("Step2-1: Reject incoming call once.")
            if not initiate_call(
                log,
                ads[2],
                ads[0].telephony['subscription'][get_incoming_voice_sub_id(
                    ads[0])]['phone_num']):
                ads[2].log.error("Initiate call failed.")
                raise _CallException("Failed to initiate call.")

            if not wait_and_reject_call_for_subscription(
                    log,
                    ads[0],
                    get_incoming_voice_sub_id(ads[0]),
                    incoming_number= \
                        ads[2].telephony['subscription'][
                            get_incoming_voice_sub_id(
                                ads[2])]['phone_num']):
                ads[0].log.error("Reject call fail.")
                raise _CallException("Failed to reject call.")

            hangup_call(log, ads[2])
            time.sleep(15)

        if not call_setup_teardown(
                log,
                ads[2],
                ads[0],
                ad_hangup=None,
                verify_caller_func=verify_func_c,
                verify_callee_func=verify_func_a):
            raise _CallException("PhoneA call PhoneC failed.")
        if not verify_incall_state(log, [ads[0], ads[1], ads[2]],
                                    True):
            raise _CallException("Not All phones are in-call.")

    except Exception as e:
        setattr(ads[0], "exception", e)
        return None

    return call_ab_id

def msim_message_test(
    log,
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
    message_lengths = (50, 160, 180)
    if msg == "SMS":
        for length in message_lengths:
            message_array = [rand_ascii_str(length)]
            if not sms_send_receive_verify_for_subscription(
                log,
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
        log.info("%s test of length %s characters succeeded.",
            msg, message_lengths)

    elif msg == "MMS":
        for length in message_lengths:
            message_array = [("Test Message", rand_ascii_str(length), None)]

            if not mms_send_receive_verify(
                log,
                ad_mo,
                ad_mt,
                message_array,
                max_wait_time,
                expected_result):
                log.warning("%s of body length %s test failed",
                    msg, length)
                return False
            else:
                log.info(
                    "%s of body length %s test succeeded", msg, length)
        log.info("%s test of body lengths %s succeeded",
                        msg, message_lengths)
    return True

def msim_call_forwarding(
        log,
        ads,
        caller_slot,
        callee_slot,
        forwarded_callee_slot,
        dds_slot,
        caller_rat=["", ""],
        callee_rat=["", ""],
        forwarded_callee_rat=["", ""],
        call_forwarding_type="unconditional"):
    """Make MO voice call to the primary device at specific slot in specific
    RAT with DDS at specific slot, and then forwarded to 3rd device with
    specific call forwarding type.

    Test step:
    1. Get sub IDs of specific slots of both MO and MT devices.
    2. Switch DDS to specific slot.
    3. Check HTTP connection after DDS switch.
    4. Set up phones in desired RAT.
    5. Register and enable call forwarding with specifc type.
    5. Make voice call to the primary device and wait for being forwarded
        to 3rd device.

    Args:
        caller_slot: Slot of 2nd device making MO call (0 or 1)
        callee_slot: Slot of primary device receiving and forwarding MT call
                        (0 or 1)
        forwarded_callee_slot: Slot of 3rd device receiving forwarded call.
        dds_slot: Preferred data slot
        caller_rat: RAT for both slots of the 2nd device
        callee_rat: RAT for both slots of the primary device
        forwarded_callee_rat: RAT for both slots of the 3rd device
        call_forwarding_type:
            "unconditional"
            "busy"
            "not_answered"
            "not_reachable"

    Returns:
        True or False
    """
    ad_caller = ads[1]
    ad_callee = ads[0]
    ad_forwarded_callee = ads[2]

    if callee_slot is not None:
        callee_sub_id = get_subid_from_slot_index(
            log, ad_callee, callee_slot)
        if callee_sub_id == INVALID_SUB_ID:
            ad_callee.log.warning(
                "Failed to get sub ID at slot %s.", callee_slot)
            return False
        callee_other_sub_id = get_subid_from_slot_index(
            log, ad_callee, 1-callee_slot)
        set_voice_sub_id(ad_callee, callee_sub_id)
    else:
        callee_sub_id, _, _ = get_subid_on_same_network_of_host_ad(ads)
        if callee_sub_id == INVALID_SUB_ID:
            ad_callee.log.warning(
                "Failed to get sub ID at slot %s.", callee_slot)
            return False
        callee_slot = "auto"
        set_voice_sub_id(ad_callee, callee_sub_id)
    ad_callee.log.info(
        "Sub ID for incoming call at slot %s: %s",
        callee_slot, get_incoming_voice_sub_id(ad_callee))

    if caller_slot is not None:
        caller_sub_id = get_subid_from_slot_index(
            log, ad_caller, caller_slot)
        if caller_sub_id == INVALID_SUB_ID:
            ad_caller.log.warning(
                "Failed to get sub ID at slot %s.", caller_slot)
            return False
        caller_other_sub_id = get_subid_from_slot_index(
            log, ad_caller, 1-caller_slot)
        set_voice_sub_id(ad_caller, caller_sub_id)
    else:
        _, caller_sub_id, _ = get_subid_on_same_network_of_host_ad(ads)
        if caller_sub_id == INVALID_SUB_ID:
            ad_caller.log.warning(
                "Failed to get sub ID at slot %s.", caller_slot)
            return False
        caller_slot = "auto"
        set_voice_sub_id(ad_caller, caller_sub_id)
    ad_caller.log.info(
        "Sub ID for outgoing call at slot %s: %s",
        caller_slot, get_outgoing_voice_sub_id(ad_caller))

    if forwarded_callee_slot is not None:
        forwarded_callee_sub_id = get_subid_from_slot_index(
            log, ad_forwarded_callee, forwarded_callee_slot)
        if forwarded_callee_sub_id == INVALID_SUB_ID:
            ad_forwarded_callee.log.warning(
                "Failed to get sub ID at slot %s.", forwarded_callee_slot)
            return False
        forwarded_callee_other_sub_id = get_subid_from_slot_index(
            log, ad_forwarded_callee, 1-forwarded_callee_slot)
        set_voice_sub_id(
            ad_forwarded_callee, forwarded_callee_sub_id)
    else:
        _, _, forwarded_callee_sub_id = \
            get_subid_on_same_network_of_host_ad(ads)
        if forwarded_callee_sub_id == INVALID_SUB_ID:
            ad_forwarded_callee.log.warning(
                "Failed to get sub ID at slot %s.", forwarded_callee_slot)
            return False
        forwarded_callee_slot = "auto"
        set_voice_sub_id(
            ad_forwarded_callee, forwarded_callee_sub_id)
    ad_forwarded_callee.log.info(
        "Sub ID for incoming call at slot %s: %s",
        forwarded_callee_slot,
        get_incoming_voice_sub_id(ad_forwarded_callee))

    log.info("Step 1: Switch DDS.")
    if not set_dds_on_slot(ads[0], dds_slot):
        log.error(
            "Failed to set DDS at slot %s on %s",(dds_slot, ads[0].serial))
        return False

    log.info("Step 2: Check HTTP connection after DDS switch.")
    if not verify_http_connection(log, ads[0]):
        log.error("Failed to verify http connection.")
        return False
    else:
        log.info("Verify http connection successfully.")

    if caller_slot == 1:
        phone_setup_on_rat(
            log,
            ad_caller,
            caller_rat[0],
            caller_other_sub_id)

    elif caller_slot == 0:
        phone_setup_on_rat(
            log,
            ad_caller,
            caller_rat[1],
            caller_other_sub_id)
    else:
        phone_setup_on_rat(
            log,
            ad_caller,
            'general')

    if callee_slot == 1:
        phone_setup_on_rat(
            log,
            ad_callee,
            callee_rat[0],
            callee_other_sub_id)

    elif callee_slot == 0:
        phone_setup_on_rat(
            log,
            ad_callee,
            callee_rat[1],
            callee_other_sub_id)
    else:
        phone_setup_on_rat(
            log,
            ad_callee,
            'general')

    if forwarded_callee_slot == 1:
        phone_setup_on_rat(
            log,
            ad_forwarded_callee,
            forwarded_callee_rat[0],
            forwarded_callee_other_sub_id)

    elif forwarded_callee_slot == 0:
        phone_setup_on_rat(
            log,
            ad_forwarded_callee,
            forwarded_callee_rat[1],
            forwarded_callee_other_sub_id)
    else:
        phone_setup_on_rat(
            log,
            ad_forwarded_callee,
            'general')

    if caller_slot == 0 or caller_slot == 1:
        caller_phone_setup_func_argv = (log, ad_caller, caller_rat[caller_slot], caller_sub_id)
    else:
        caller_phone_setup_func_argv = (log, ad_caller, 'general')

    callee_phone_setup_func_argv = (log, ad_callee, callee_rat[callee_slot], callee_sub_id)

    if forwarded_callee_slot == 0 or forwarded_callee_slot == 1:
        forwarded_callee_phone_setup_func_argv = (
            log,
            ad_forwarded_callee,
            forwarded_callee_rat[forwarded_callee_slot],
            forwarded_callee_sub_id)
    else:
        forwarded_callee_phone_setup_func_argv = (
            log,
            ad_forwarded_callee,
            'general')

    log.info("Step 3: Set up phones in desired RAT.")
    tasks = [(phone_setup_on_rat, caller_phone_setup_func_argv),
                (phone_setup_on_rat, callee_phone_setup_func_argv),
                (phone_setup_on_rat,
                forwarded_callee_phone_setup_func_argv)]
    if not multithread_func(log, tasks):
        log.error("Phone Failed to Set Up Properly.")
        tel_logger.set_result(CallResult("CALL_SETUP_FAILURE"))
        raise signals.TestFailure("Failed",
            extras={"fail_reason": "Phone Failed to Set Up Properly."})

    is_callee_in_call = is_phone_in_call_on_rat(
        log, ad_callee, callee_rat[callee_slot], only_return_fn=True)

    is_call_waiting = re.search(
        "call_waiting (True (\d)|False)", call_forwarding_type, re.I)
    if is_call_waiting:
        if is_call_waiting.group(1) == "False":
            call_waiting = False
            scenario = None
        else:
            call_waiting = True
            scenario = int(is_call_waiting.group(2))

        log.info(
            "Step 4: Make voice call with call waiting enabled = %s.",
            call_waiting)
        result = three_phone_call_waiting_short_seq(
            log,
            ads[0],
            None,
            is_callee_in_call,
            ads[1],
            ads[2],
            call_waiting=call_waiting, scenario=scenario)
    else:
        log.info(
            "Step 4: Make voice call with call forwarding %s.",
            call_forwarding_type)
        result = three_phone_call_forwarding_short_seq(
            log,
            ads[0],
            None,
            is_callee_in_call,
            ads[1],
            ads[2],
            call_forwarding_type=call_forwarding_type)

    if not result:
        if is_call_waiting:
            pass
        else:
            log.error(
                "Failed to make MO call from %s slot %s to %s slot %s"
                " and forward to %s slot %s",
                ad_caller.serial,
                caller_slot,
                ad_callee.serial,
                callee_slot,
                ad_forwarded_callee.serial,
                forwarded_callee_slot)

    return result

def msim_call_voice_conf(
        log,
        ads,
        host_slot,
        p1_slot,
        p2_slot,
        dds_slot,
        host_rat=["volte", "volte"],
        p1_rat="",
        p2_rat="",
        merge=True,
        disable_cw=False):
    """Make a voice conference call at specific slot in specific RAT with
    DDS at specific slot.

    Test step:
    1. Get sub IDs of specific slots of both MO and MT devices.
    2. Switch DDS to specific slot.
    3. Check HTTP connection after DDS switch.
    4. Set up phones in desired RAT and make 3-way voice call.
    5. Swap calls.
    6. Merge calls.

    Args:
        host_slot: Slot on the primary device to host the comference call.
        0 or 1 (0 for pSIM or 1 for eSIM)
        p1_slot: Slot on the participant device for the call
        p2_slot: Slot on another participant device for the call
        dds_slot: Preferred data slot
        host_rat: RAT for both slots of the primary device
        p1_rat: RAT for both slots of the participant device
        p2_rat: RAT for both slots of another participant device
        merge: True for merging 2 calls into the conference call. False for
        not merging 2 separated call.
        disable_cw: True for disabling call waiting and False on the
        contrary.

    Returns:
        True or False
    """
    ad_host = ads[0]
    ad_p1 = ads[1]
    ad_p2 = ads[2]

    if host_slot is not None:
        host_sub_id = get_subid_from_slot_index(
            log, ad_host, host_slot)
        if host_sub_id == INVALID_SUB_ID:
            ad_host.log.warning("Failed to get sub ID at slot.", host_slot)
            return False
        host_other_sub_id = get_subid_from_slot_index(
            log, ad_host, 1-host_slot)
        set_voice_sub_id(ad_host, host_sub_id)
    else:
        host_sub_id, _, _ = get_subid_on_same_network_of_host_ad(ads)
        if host_sub_id == INVALID_SUB_ID:
            ad_host.log.warning("Failed to get sub ID at slot.", host_slot)
            return False
        host_slot = "auto"
        set_voice_sub_id(ad_host, host_sub_id)

    ad_host.log.info("Sub ID for outgoing call at slot %s: %s",
        host_slot, get_outgoing_voice_sub_id(ad_host))

    if p1_slot is not None:
        p1_sub_id = get_subid_from_slot_index(log, ad_p1, p1_slot)
        if p1_sub_id == INVALID_SUB_ID:
            ad_p1.log.warning("Failed to get sub ID at slot %s.", p1_slot)
            return False
        set_voice_sub_id(ad_p1, p1_sub_id)
    else:
        _, p1_sub_id, _ = get_subid_on_same_network_of_host_ad(ads)
        if p1_sub_id == INVALID_SUB_ID:
            ad_p1.log.warning("Failed to get sub ID at slot %s.", p1_slot)
            return False
        p1_slot = "auto"
        set_voice_sub_id(ad_p1, p1_sub_id)
    ad_p1.log.info("Sub ID for incoming call at slot %s: %s",
        p1_slot, get_incoming_voice_sub_id(ad_p1))

    if p2_slot is not None:
        p2_sub_id = get_subid_from_slot_index(log, ad_p2, p2_slot)
        if p2_sub_id == INVALID_SUB_ID:
            ad_p2.log.warning("Failed to get sub ID at slot %s.", p2_slot)
            return False
        set_voice_sub_id(ad_p2, p2_sub_id)
    else:
        _, _, p2_sub_id = get_subid_on_same_network_of_host_ad(ads)
        if p2_sub_id == INVALID_SUB_ID:
            ad_p2.log.warning("Failed to get sub ID at slot %s.", p2_slot)
            return False
        p2_slot = "auto"
        set_voice_sub_id(ad_p2, p2_sub_id)
    ad_p2.log.info("Sub ID for incoming call at slot %s: %s",
        p2_slot, get_incoming_voice_sub_id(ad_p2))

    log.info("Step 1: Switch DDS.")
    if not set_dds_on_slot(ads[0], dds_slot):
        log.error(
            "Failed to set DDS at slot %s on %s",(dds_slot, ads[0].serial))
        return False

    log.info("Step 2: Check HTTP connection after DDS switch.")
    if not verify_http_connection(log, ads[0]):
        log.error("Failed to verify http connection.")
        return False
    else:
        log.info("Verify http connection successfully.")

    if disable_cw:
        if not set_call_waiting(log, ad_host, enable=0):
            return False
    else:
        if not set_call_waiting(log, ad_host, enable=1):
            return False

    if host_slot == 1:
        phone_setup_on_rat(
            log,
            ad_host,
            host_rat[0],
            host_other_sub_id)

    elif host_slot == 0:
        phone_setup_on_rat(
            log,
            ad_host,
            host_rat[1],
            host_other_sub_id)

    if host_slot == 0 or host_slot == 1:
        host_phone_setup_func_argv = (log, ad_host, host_rat[host_slot], host_sub_id)
        is_host_in_call = is_phone_in_call_on_rat(
            log, ad_host, host_rat[host_slot], only_return_fn=True)
    else:
        host_phone_setup_func_argv = (log, ad_host, 'general')
        is_host_in_call = is_phone_in_call_on_rat(
            log, ad_host, 'general', only_return_fn=True)

    if p1_rat:
        p1_phone_setup_func_argv = (log, ad_p1, p1_rat, p1_sub_id)
        is_p1_in_call = is_phone_in_call_on_rat(
            log, ad_p1, p1_rat, only_return_fn=True)
    else:
        p1_phone_setup_func_argv = (log, ad_p1, 'general')
        is_p1_in_call = is_phone_in_call_on_rat(
            log, ad_p1, 'general', only_return_fn=True)

    if p2_rat:
        p2_phone_setup_func_argv = (log, ad_p2, p2_rat, p2_sub_id)
        is_p2_in_call = is_phone_in_call_on_rat(
            log, ad_p2, p2_rat, only_return_fn=True)
    else:
        p2_phone_setup_func_argv = (log, ad_p2, 'general')
        is_p2_in_call = is_phone_in_call_on_rat(
            log, ad_p2, 'general', only_return_fn=True)

    log.info("Step 3: Set up phone in desired RAT and make 3-way"
        " voice call.")

    tasks = [(phone_setup_on_rat, host_phone_setup_func_argv),
                (phone_setup_on_rat, p1_phone_setup_func_argv),
                (phone_setup_on_rat, p2_phone_setup_func_argv)]
    if not multithread_func(log, tasks):
        log.error("Phone Failed to Set Up Properly.")
        tel_logger.set_result(CallResult("CALL_SETUP_FAILURE"))
        raise signals.TestFailure("Failed",
            extras={"fail_reason": "Phone Failed to Set Up Properly."})

    call_ab_id = three_way_calling_mo_and_mt_with_hangup_once(
        log,
        [ad_host, ad_p1, ad_p2],
        [None, None, None], [
            is_host_in_call, is_p1_in_call,
            is_p2_in_call
        ])

    if call_ab_id is None:
        if disable_cw:
            set_call_waiting(log, ad_host, enable=1)
            if str(getattr(ad_host, "exception", None)) == \
                "PhoneA call PhoneC failed.":
                ads[0].log.info("PhoneA failed to call PhoneC due to call"
                    " waiting being disabled.")
                delattr(ad_host, "exception")
                return True
        log.error("Failed to get call_ab_id")
        return False
    else:
        if disable_cw:
            return False

    calls = ads[0].droid.telecomCallGetCallIds()
    ads[0].log.info("Calls in PhoneA %s", calls)
    if num_active_calls(log, ads[0]) != 2:
        return False
    if calls[0] == call_ab_id:
        call_ac_id = calls[1]
    else:
        call_ac_id = calls[0]

    if call_ac_id is None:
        log.error("Failed to get call_ac_id")
        return False

    num_swaps = 2
    log.info("Step 4: Begin Swap x%s test.", num_swaps)
    if not swap_calls(log, ads, call_ab_id, call_ac_id,
                        num_swaps):
        log.error("Swap test failed.")
        return False

    if not merge:
        result = True
        if not hangup_call(log, ads[1]):
            result =  False
        if not hangup_call(log, ads[2]):
            result =  False
        return result
    else:
        log.info("Step 5: Merge calls.")
        if host_rat[host_slot] == "volte":
            return _test_ims_conference_merge_drop_second_call_from_participant(
                log, ads, call_ab_id, call_ac_id)
        else:
            return _test_wcdma_conference_merge_drop(
                log, ads, call_ab_id, call_ac_id)

def msim_volte_wfc_call_forwarding(
        log,
        ads,
        callee_slot,
        dds_slot,
        callee_rat=["5g_wfc", "5g_wfc"],
        call_forwarding_type="unconditional",
        is_airplane_mode=False,
        is_wifi_connected=False,
        wfc_mode=[
            WFC_MODE_CELLULAR_PREFERRED,
            WFC_MODE_CELLULAR_PREFERRED],
        wifi_network_ssid=None,
        wifi_network_pass=None):
    """Make VoLTE/WFC call to the primary device at specific slot with DDS
    at specific slot, and then forwarded to 3rd device with specific call
    forwarding type.

    Test step:
    1. Get sub IDs of specific slots of both MO and MT devices.
    2. Switch DDS to specific slot.
    3. Check HTTP connection after DDS switch.
    4. Set up phones in desired RAT.
    5. Register and enable call forwarding with specifc type.
    6. Make VoLTE/WFC call to the primary device and wait for being
        forwarded to 3rd device.

    Args:
        callee_slot: Slot of primary device receiving and forwarding MT call
                        (0 or 1)
        dds_slot: Preferred data slot
        callee_rat: RAT for both slots of the primary device
        call_forwarding_type:
            "unconditional"
            "busy"
            "not_answered"
            "not_reachable"
        is_airplane_mode: True or False for WFC setup
        wfc_mode: Cellular preferred or Wi-Fi preferred.
        wifi_network_ssid: SSID of Wi-Fi AP
        wifi_network_pass: Password of Wi-Fi AP SSID

    Returns:
        True or False
    """
    ad_caller = ads[1]
    ad_callee = ads[0]
    ad_forwarded_callee = ads[2]

    if not toggle_airplane_mode(log, ad_callee, False):
        ad_callee.log.error("Failed to disable airplane mode.")
        return False

    # Set up callee (primary device)
    callee_sub_id = get_subid_from_slot_index(
        log, ad_callee, callee_slot)
    if callee_sub_id == INVALID_SUB_ID:
        log.warning(
            "Failed to get sub ID at slot %s.", callee_slot)
        return
    callee_other_sub_id = get_subid_from_slot_index(
        log, ad_callee, 1-callee_slot)
    set_voice_sub_id(ad_callee, callee_sub_id)
    ad_callee.log.info(
        "Sub ID for incoming call at slot %s: %s",
        callee_slot, get_incoming_voice_sub_id(ad_callee))

    # Set up caller
    _, caller_sub_id, _ = get_subid_on_same_network_of_host_ad(ads)
    if caller_sub_id == INVALID_SUB_ID:
        ad_caller.log.warning("Failed to get proper sub ID of the caller")
        return
    set_voice_sub_id(ad_caller, caller_sub_id)
    ad_caller.log.info(
        "Sub ID for outgoing call of the caller: %s",
        get_outgoing_voice_sub_id(ad_caller))

    # Set up forwarded callee
    _, _, forwarded_callee_sub_id = get_subid_on_same_network_of_host_ad(
        ads)
    if forwarded_callee_sub_id == INVALID_SUB_ID:
        ad_forwarded_callee.log.warning(
            "Failed to get proper sub ID of the forwarded callee.")
        return
    set_voice_sub_id(ad_forwarded_callee, forwarded_callee_sub_id)
    ad_forwarded_callee.log.info(
        "Sub ID for incoming call of the forwarded callee: %s",
        get_incoming_voice_sub_id(ad_forwarded_callee))

    log.info("Step 1: Switch DDS.")
    if not set_dds_on_slot(ads[0], dds_slot):
        log.error(
            "Failed to set DDS at slot %s on %s",(dds_slot, ads[0].serial))
        return False

    log.info("Step 2: Check HTTP connection after DDS switch.")
    if not verify_http_connection(log, ad_callee):
        ad_callee.log.error("Failed to verify http connection.")
        return False
    else:
        ad_callee.log.info("Verify http connection successfully.")

    is_callee_in_call = is_phone_in_call_on_rat(
        log, ad_callee, callee_rat[callee_slot], only_return_fn=True)

    if is_airplane_mode:
        set_call_forwarding_by_mmi(log, ad_callee, ad_forwarded_callee)

    log.info("Step 3: Set up phones in desired RAT.")
    if callee_slot == 1:
        phone_setup_on_rat(
            log,
            ad_callee,
            callee_rat[0],
            callee_other_sub_id,
            is_airplane_mode,
            wfc_mode[0],
            wifi_network_ssid,
            wifi_network_pass)

    elif callee_slot == 0:
        phone_setup_on_rat(
            log,
            ad_callee,
            callee_rat[1],
            callee_other_sub_id,
            is_airplane_mode,
            wfc_mode[1],
            wifi_network_ssid,
            wifi_network_pass)

    argv = (
        log,
        ad_callee,
        callee_rat[callee_slot],
        callee_sub_id,
        is_airplane_mode,
        wfc_mode[callee_slot],
        wifi_network_ssid,
        wifi_network_pass)

    tasks = [(phone_setup_voice_general, (log, ad_caller)),
            (phone_setup_on_rat, argv),
            (phone_setup_voice_general, (log, ad_forwarded_callee))]

    if not multithread_func(log, tasks):
        log.error("Phone Failed to Set Up Properly.")
        tel_logger.set_result(CallResult("CALL_SETUP_FAILURE"))
        raise signals.TestFailure("Failed",
            extras={"fail_reason": "Phone Failed to Set Up Properly."})

    if is_wifi_connected:
        if not ensure_wifi_connected(
            log,
            ad_callee,
            wifi_network_ssid,
            wifi_network_pass,
            apm=is_airplane_mode):
            return False
        time.sleep(5)

    if "wfc" not in callee_rat[callee_slot]:
        if not toggle_wfc_for_subscription(
            log,
            ad_callee,
            new_state=True,
            sub_id=callee_sub_id):
            return False
        if not set_wfc_mode_for_subscription(
            ad_callee, wfc_mode[callee_slot], sub_id=callee_sub_id):
            return False

    log.info(
        "Step 4: Make voice call with call forwarding %s.",
        call_forwarding_type)
    result = three_phone_call_forwarding_short_seq(
        log,
        ad_callee,
        None,
        is_callee_in_call,
        ad_caller,
        ad_forwarded_callee,
        call_forwarding_type=call_forwarding_type)

    if not result:
        log.error(
            "Failed to make MO call from %s to %s slot %s and forward"
            " to %s.",
            ad_caller.serial,
            ad_callee.serial,
            callee_slot,
            ad_forwarded_callee.serial)
    return result

def msim_volte_wfc_call_voice_conf(
        log,
        ads,
        host_slot,
        dds_slot,
        host_rat=["5g_wfc", "5g_wfc"],
        merge=True,
        disable_cw=False,
        is_airplane_mode=False,
        is_wifi_connected=False,
        wfc_mode=[WFC_MODE_CELLULAR_PREFERRED, WFC_MODE_CELLULAR_PREFERRED],
        reject_once=False,
        wifi_network_ssid=None,
        wifi_network_pass=None):
    """Make a VoLTE/WFC conference call at specific slot with DDS at
        specific slot.

    Test step:
    1. Get sub IDs of specific slots of both MO and MT devices.
    2. Set up phones in desired RAT
    3. Enable VoLTE/WFC.
    4. Switch DDS to specific slot.
    5. Check HTTP connection after DDS switch.
    6. Make 3-way VoLTE/WFC call.
    7. Swap calls.
    8. Merge calls.

    Args:
        host_slot: Slot on the primary device to host the comference call.
                    0 or 1 (0 for pSIM or 1 for eSIM)call
        dds_slot: Preferred data slot
        host_rat: RAT for both slots of the primary devicevice
        merge: True for merging 2 calls into the conference call. False for
                not merging 2 separated call.
        disable_cw: True for disabling call waiting and False on the
                    contrary.
        enable_volte: True for enabling and False for disabling VoLTE for
                        each slot on the primary device
        enable_wfc: True for enabling and False for disabling WFC for
                    each slot on the primary device
        is_airplane_mode: True or False for WFC setup
        wfc_mode: Cellular preferred or Wi-Fi preferred.
        reject_once: True for rejecting the 2nd call once from the 3rd
                        device (Phone C) to the primary device (Phone A).
        wifi_network_ssid: SSID of Wi-Fi AP
        wifi_network_pass: Password of Wi-Fi AP SSID

    Returns:
        True or False
    """
    ad_host = ads[0]
    ad_p1 = ads[1]
    ad_p2 = ads[2]

    host_sub_id = get_subid_from_slot_index(log, ad_host, host_slot)
    if host_sub_id == INVALID_SUB_ID:
        ad_host.log.warning("Failed to get sub ID at slot.", host_slot)
        return
    host_other_sub_id = get_subid_from_slot_index(
        log, ad_host, 1-host_slot)
    set_voice_sub_id(ad_host, host_sub_id)
    ad_host.log.info(
        "Sub ID for outgoing call at slot %s: %s",
        host_slot, get_outgoing_voice_sub_id(ad_host))

    _, p1_sub_id, p2_sub_id = get_subid_on_same_network_of_host_ad(ads)

    if p1_sub_id == INVALID_SUB_ID:
        ad_p1.log.warning("Failed to get proper sub ID.")
        return
    set_voice_sub_id(ad_p1, p1_sub_id)
    ad_p1.log.info(
        "Sub ID for incoming call: %s",
        get_incoming_voice_sub_id(ad_p1))

    if p2_sub_id == INVALID_SUB_ID:
        ad_p2.log.warning("Failed to get proper sub ID.")
        return
    set_voice_sub_id(ad_p2, p2_sub_id)
    ad_p2.log.info(
        "Sub ID for incoming call: %s", get_incoming_voice_sub_id(ad_p2))

    log.info("Step 1: Switch DDS.")
    if not set_dds_on_slot(ads[0], dds_slot):
        log.error(
            "Failed to set DDS at slot %s on %s",(dds_slot, ads[0].serial))
        return False

    log.info("Step 2: Check HTTP connection after DDS switch.")
    if not verify_http_connection(log, ads[0]):
        ad_host.log.error("Failed to verify http connection.")
        return False
    else:
        ad_host.log.info("Verify http connection successfully.")

    if disable_cw:
        if not set_call_waiting(log, ad_host, enable=0):
            return False

    log.info("Step 3: Set up phones in desired RAT.")
    if host_slot == 1:
        phone_setup_on_rat(
            log,
            ad_host,
            host_rat[0],
            host_other_sub_id,
            is_airplane_mode,
            wfc_mode[0],
            wifi_network_ssid,
            wifi_network_pass)

    elif host_slot == 0:
        phone_setup_on_rat(
            log,
            ad_host,
            host_rat[1],
            host_other_sub_id,
            is_airplane_mode,
            wfc_mode[1],
            wifi_network_ssid,
            wifi_network_pass)

    argv = (
        log,
        ad_host,
        host_rat[host_slot],
        host_sub_id,
        is_airplane_mode,
        wfc_mode[host_slot],
        wifi_network_ssid,
        wifi_network_pass)

    tasks = [(phone_setup_voice_general, (log, ad_p1)),
            (phone_setup_on_rat, argv),
            (phone_setup_voice_general, (log, ad_p2))]

    if not multithread_func(log, tasks):
        log.error("Phone Failed to Set Up Properly.")
        tel_logger.set_result(CallResult("CALL_SETUP_FAILURE"))
        raise signals.TestFailure("Failed",
            extras={"fail_reason": "Phone Failed to Set Up Properly."})

    if is_wifi_connected:
        if not ensure_wifi_connected(
            log,
            ad_host,
            wifi_network_ssid,
            wifi_network_pass,
            apm=is_airplane_mode):
            return False
        time.sleep(5)

    if "wfc" not in host_rat[host_slot]:
        if not toggle_wfc_for_subscription(
            log,
            ad_host,
            new_state=True,
            sub_id=host_sub_id):
            return False
        if not set_wfc_mode_for_subscription(
            ad_host, wfc_mode[host_slot], sub_id=host_sub_id):
            return False

    log.info("Step 4: Make 3-way voice call.")
    is_host_in_call = is_phone_in_call_on_rat(
        log, ad_host, host_rat[host_slot], only_return_fn=True)
    call_ab_id = _three_phone_call_mo_add_mt(
        log,
        [ad_host, ad_p1, ad_p2],
        [None, None, None],
        [is_host_in_call, None, None],
        reject_once=reject_once)

    if call_ab_id is None:
        if disable_cw:
            set_call_waiting(log, ad_host, enable=1)
            if str(getattr(ad_host, "exception", None)) == \
                "PhoneA call PhoneC failed.":
                ads[0].log.info("PhoneA failed to call PhoneC due to call"
                " waiting being disabled.")
                delattr(ad_host, "exception")
                return True
        log.error("Failed to get call_ab_id")
        return False
    else:
        if disable_cw:
            set_call_waiting(log, ad_host, enable=0)
            return False

    calls = ads[0].droid.telecomCallGetCallIds()
    ads[0].log.info("Calls in PhoneA %s", calls)
    if num_active_calls(log, ads[0]) != 2:
        return False
    if calls[0] == call_ab_id:
        call_ac_id = calls[1]
    else:
        call_ac_id = calls[0]

    if call_ac_id is None:
        log.error("Failed to get call_ac_id")
        return False

    num_swaps = 2
    log.info("Step 5: Begin Swap x%s test.", num_swaps)
    if not swap_calls(log, ads, call_ab_id, call_ac_id,
                        num_swaps):
        ad_host.log.error("Swap test failed.")
        return False

    if not merge:
        result = True
        if not hangup_call(log, ads[1]):
            result =  False
        if not hangup_call(log, ads[2]):
            result =  False
        return result
    else:
        log.info("Step 6: Merge calls.")

        if re.search('csfb|2g|3g', host_rat[host_slot].lower(), re.I):
            return _test_wcdma_conference_merge_drop(
                log, ads, call_ab_id, call_ac_id)
        else:
            return _test_ims_conference_merge_drop_second_call_from_participant(
                log, ads, call_ab_id, call_ac_id)