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
from acts_contrib.test_utils.tel.tel_test_utils import mms_send_receive_verify

message_lengths = (50, 160, 180)
long_message_lengths = (800, 1600)

def _mms_test_mo(log, ads, expected_result=True):
    return _mms_test(log,
        [ads[0], ads[1]], expected_result=expected_result)

def _mms_test_mt(log, ads, expected_result=True):
    return _mms_test(log,
        [ads[1], ads[0]], expected_result=expected_result)

def _mms_test(log, ads, expected_result=True):
    """Test MMS between two phones.

    Returns:
        True if success.
        False if failed.
    """
    for length in message_lengths:
        message_array = [("Test Message", rand_ascii_str(length), None)]
        if not mms_send_receive_verify(
                log,
                ads[0],
                ads[1],
                message_array,
                expected_result=expected_result):
            log.warning("MMS of body length %s test failed", length)
            return False
        else:
            log.info("MMS of body length %s test succeeded", length)
    log.info("MMS test of body lengths %s succeeded",
                  message_lengths)
    return True

def _long_mms_test_mo(log, ads):
    return _long_mms_test(log, [ads[0], ads[1]])

def _long_mms_test_mt(log, ads):
    return _long_mms_test(log, [ads[1], ads[0]])

def _long_mms_test(log, ads):
    """Test MMS between two phones.

    Returns:
        True if success.
        False if failed.
    """
    for length in long_message_lengths:
        message_array = [("Test Message", rand_ascii_str(length), None)]
        if not mms_send_receive_verify(log, ads[0], ads[1],
                                       message_array):
            log.warning("MMS of body length %s test failed", length)
            return False
        else:
            log.info("MMS of body length %s test succeeded", length)
            time.sleep(30)
    log.info("MMS test of body lengths %s succeeded",
                  message_lengths)
    return True

