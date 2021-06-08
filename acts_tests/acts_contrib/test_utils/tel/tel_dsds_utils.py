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

from acts import asserts
from acts import signals
from acts_contrib.test_utils.tel.loggers.protos.telephony_metric_pb2 import TelephonyVoiceTestResult
from acts_contrib.test_utils.tel.loggers.telephony_metric_logger import TelephonyMetricLogger
from acts_contrib.test_utils.tel.tel_defines import INVALID_SUB_ID
from acts_contrib.test_utils.tel.tel_subscription_utils import get_incoming_voice_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_outgoing_voice_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_from_slot_index
from acts_contrib.test_utils.tel.tel_subscription_utils import set_voice_sub_id
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_0
from acts_contrib.test_utils.tel.tel_subscription_utils import set_dds_on_slot_1
from acts_contrib.test_utils.tel.tel_subscription_utils import get_subid_on_same_network_of_host_ad
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import verify_http_connection
from acts_contrib.test_utils.tel.tel_test_utils import get_slot_index_from_subid
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import two_phone_call_msim_for_slot

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
    if dds:
        if not set_dds_on_slot_1(ads[0]):
            ads[0].log.warning("Failed to set DDS at eSIM.")
            return False
    else:
        if not set_dds_on_slot_0(ads[0]):
            ads[0].log.warning("Failed to set DDS at pSIM.")
            return False

    log.info("Step 2: Check HTTP connection after DDS switch.")
    if not verify_http_connection(log,
        ads[0],
        url="https://www.google.com",
        retry=5,
        retry_interval=15,
        expected_state=True):

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