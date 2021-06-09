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
from acts.utils import rand_ascii_str
from acts_contrib.test_utils.tel.tel_defines import SMS_OVER_WIFI_PROVIDERS
from acts_contrib.test_utils.tel.tel_defines import WAIT_TIME_ANDROID_STATE_SETTLING
from acts_contrib.test_utils.tel.tel_defines import VT_STATE_BIDIRECTIONAL
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_DISABLED
from acts_contrib.test_utils.tel.tel_test_utils import call_setup_teardown
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import hangup_call
from acts_contrib.test_utils.tel.tel_test_utils import sms_send_receive_verify
from acts_contrib.test_utils.tel.tel_test_utils import mms_send_receive_verify
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import mms_receive_verify_after_call_hangup
from acts_contrib.test_utils.tel.tel_subscription_utils import get_outgoing_message_sub_id
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_on_rat
from acts_contrib.test_utils.tel.tel_voice_utils import is_phone_in_call_on_rat
from acts_contrib.test_utils.tel.tel_video_utils import is_phone_in_call_video_bidirectional
from acts_contrib.test_utils.tel.tel_video_utils import video_call_setup_teardown
from acts_contrib.test_utils.tel.tel_video_utils import phone_idle_video

def send_message_with_random_message_body(
    log, ad_mo, ad_mt, msg_type='sms', long_msg=False, mms_expected_result=True):
    """Test SMS/MMS between two phones.
    Returns:
        True if success.
        False if failed.
    """
    message_lengths = (50, 160, 180)

    if long_msg:
        message_lengths = (800, 1600)
        message_lengths_of_jp_carriers = (800, 1530)
        sender_message_sub_id = get_outgoing_message_sub_id(ad_mo)
        sender_mcc = ad_mo.telephony["subscription"][sender_message_sub_id]["mcc"]
        if str(sender_mcc) in ["440", "441"]:
            message_lengths = message_lengths_of_jp_carriers

    if msg_type == 'sms':
        for length in message_lengths:
            message_array = [rand_ascii_str(length)]
            if not sms_send_receive_verify(log, ad_mo, ad_mt, message_array):
                ad_mo.log.error("SMS of length %s test failed", length)
                return False
            else:
                ad_mo.log.info("SMS of length %s test succeeded", length)
        log.info("SMS test of length %s characters succeeded.",
                    message_lengths)
    elif msg_type == 'mms':
        is_roaming = False
        for ad in [ad_mo, ad_mt]:
            ad.sms_over_wifi = False
            # verizon supports sms over wifi. will add more carriers later
            for sub in ad.telephony["subscription"].values():
                if sub["operator"] in SMS_OVER_WIFI_PROVIDERS:
                    ad.sms_over_wifi = True

            if getattr(ad, 'roaming', False):
                is_roaming = True

        if is_roaming:
            # roaming device does not allow message of length 180
            message_lengths = (50, 160)

        for length in message_lengths:
            message_array = [("Test Message", rand_ascii_str(length), None)]
            result = True
            if not mms_send_receive_verify(
                    log,
                    ad_mo,
                    ad_mt,
                    message_array,
                    expected_result=mms_expected_result):

                if mms_expected_result is True:
                    if ad_mo.droid.telecomIsInCall() or ad_mt.droid.telecomIsInCall():
                        if not mms_receive_verify_after_call_hangup(
                            log, ad_mo, ad_mt, message_array):
                            result = False
                    else:
                        result = False

                if not result:
                    log.error("MMS of body length %s test failed", length)
                    return False
            else:
                log.info("MMS of body length %s test succeeded", length)
        log.info("MMS test of body lengths %s succeeded", message_lengths)
    return True

def message_test(
    log,
    ad_mo,
    ad_mt,
    mo_rat='general',
    mt_rat='general',
    msg_type='sms',
    long_msg=False,
    mms_expected_result=True,
    msg_in_call=False,
    video_or_voice='voice',
    is_airplane_mode=False,
    wfc_mode=None,
    wifi_ssid=None,
    wifi_pwd=None):

    mo_phone_setup_argv = (
        log, ad_mo, 'general', None, False, None, None, None, None, 'sms')
    mt_phone_setup_argv = (
        log, ad_mt, 'general', None, False, None, None, None, None, 'sms')
    verify_caller_func = None
    verify_callee_func = None

    if mo_rat:
        mo_phone_setup_argv = (
            log,
            ad_mo,
            mo_rat,
            None,
            is_airplane_mode,
            wfc_mode,
            wifi_ssid,
            wifi_pwd,
            None,
            'sms')
        verify_caller_func = is_phone_in_call_on_rat(
            log, ad_mo, rat=mo_rat, only_return_fn=True)

    if mt_rat:
        mt_phone_setup_argv = (
            log,
            ad_mt,
            mt_rat,
            None,
            is_airplane_mode,
            wfc_mode,
            wifi_ssid,
            wifi_pwd,
            None,
            'sms')
        verify_callee_func = is_phone_in_call_on_rat(
            log, ad_mo, rat=mt_rat, only_return_fn=True)

    tasks = [(phone_setup_on_rat, mo_phone_setup_argv),
                (phone_setup_on_rat, mt_phone_setup_argv)]
    if not multithread_func(log, tasks):
        log.error("Phone Failed to Set Up Properly.")
        return False
    time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)

    if wifi_ssid:
        if not wfc_mode or wfc_mode == WFC_MODE_DISABLED:
            tasks = [(ensure_wifi_connected, (log, ad_mo, wifi_ssid, wifi_pwd)),
                    (ensure_wifi_connected, (log, ad_mt, wifi_ssid, wifi_pwd))]
            if not multithread_func(log, tasks):
                log.error("Failed to connected to Wi-Fi.")
                return False

    if msg_in_call:
        if video_or_voice == 'voice':
            if not call_setup_teardown(
                    log,
                    ad_mo,
                    ad_mt,
                    ad_hangup=None,
                    verify_caller_func=verify_caller_func,
                    verify_callee_func=verify_callee_func):
                log.error("Failed to setup a voice call")
                return False
        elif video_or_voice == 'video':
            tasks = [
                (phone_idle_video, (log, ad_mo)),
                (phone_idle_video, (log, ad_mt))]
            if not multithread_func(log, tasks):
                log.error("Phone Failed to Set Up Properly.")
                return False
            time.sleep(WAIT_TIME_ANDROID_STATE_SETTLING)
            if not video_call_setup_teardown(
                    log,
                    ad_mo,
                    ad_mt,
                    None,
                    video_state=VT_STATE_BIDIRECTIONAL,
                    verify_caller_func=is_phone_in_call_video_bidirectional,
                    verify_callee_func=is_phone_in_call_video_bidirectional):
                log.error("Failed to setup a video call")
                return False

    result = True
    if not send_message_with_random_message_body(
        log, ad_mo, ad_mt, msg_type, long_msg, mms_expected_result):
        log.error("Test failed.")
        result = False

    if msg_in_call:
        if not hangup_call(log, ad_mo):
            ad_mo.log.info("Failed to hang up call!")
            result = False

    return result