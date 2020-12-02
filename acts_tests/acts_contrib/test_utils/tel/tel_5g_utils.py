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

import time
import random
import re

from acts.utils import rand_ascii_str
from acts_contrib.test_utils.tel.tel_defines import NETWORK_MODE_NR_LTE_GSM_WCDMA
from acts_contrib.test_utils.tel.tel_defines import OverrideNetworkContainer
from acts_contrib.test_utils.tel.tel_defines import DisplayInfoContainer
from acts_contrib.test_utils.tel.tel_defines import EventDisplayInfoChanged
from acts_contrib.test_utils.tel.tel_test_utils import set_preferred_network_mode_pref
from acts_contrib.test_utils.tel.tel_test_utils import is_event_match


def is_current_network_5g_nsa(ad, timeout=30):
    """Verifies 5G NSA override network type

    Args:
        ad: android device object.
        timeout: max time to wait for event

    Returns:
        True: if data is on nsa5g NSA
        False: if data is not on nsa5g NSA
    """
    ad.ed.clear_events(EventDisplayInfoChanged)
    ad.droid.telephonyStartTrackingDisplayInfoChange()
    try:
        event = ad.ed.wait_for_event(
                EventDisplayInfoChanged,
                is_event_match,
                timeout=timeout,
                field=DisplayInfoContainer.OVERRIDE,
                value=OverrideNetworkContainer.OVERRIDE_NETWORK_TYPE_NR_NSA)
        ad.log.info("Got expected event %s", event)
        return True
    except Empty:
        ad.log.info("No event for display info change")
        return False
    finally:
        ad.droid.telephonyStopTrackingDisplayInfoChange()
    return None


def set_preferred_mode_for_5g(ad, sub_id=None, mode=None):
    """Set Preferred Network Mode for 5G NSA
    Args:
        ad: Android device object.
        sub_id: Subscription ID.
        mode: 5G Network Mode Type
    """
    if sub_id is None:
        sub_id = ad.droid.subscriptionGetDefaultSubId()
    if mode is None:
        mode = NETWORK_MODE_NR_LTE_GSM_WCDMA
    return set_preferred_network_mode_pref(ad.log, ad, sub_id, mode)