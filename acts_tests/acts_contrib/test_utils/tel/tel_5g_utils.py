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
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_CELLULAR_PREFERRED
from acts_contrib.test_utils.tel.tel_defines import WFC_MODE_WIFI_PREFERRED
from acts_contrib.test_utils.tel.tel_test_utils import set_preferred_network_mode_pref
from acts_contrib.test_utils.tel.tel_test_utils import is_event_match
from acts_contrib.test_utils.tel.tel_test_utils import multithread_func
from acts_contrib.test_utils.tel.tel_test_utils import ensure_wifi_connected
from acts_contrib.test_utils.tel.tel_test_utils import toggle_airplane_mode
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_volte
from acts_contrib.test_utils.tel.tel_voice_utils import phone_setup_iwlan


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


def provision_both_devices_for_5g(log, ads):
    # Mode Pref
    tasks = [(set_preferred_mode_for_5g, [ad]) for ad in ads]
    if not multithread_func(log, tasks):
        log.error("failed to set preferred network mode on 5g")
        return False
    # Attach
    tasks = [(is_current_network_5g_nsa, [ad]) for ad in ads]
    if not multithread_func(log, tasks):
        log.error("phone not on 5g nsa")
        return False
    return True


def provision_both_devices_for_volte(log, ads):
    # LTE attach and enable VoLTE on both phones
    tasks = [(phone_setup_volte, (log, ads[0])),
             (phone_setup_volte, (log, ads[1]))]
    if not multithread_func(log, tasks):
        log.error("phone failed to set up in volte")
        return False
    return True


def verify_5g_attach_for_both_devices(log, ads):
    # Attach
    tasks = [(is_current_network_5g_nsa, [ad]) for ad in ads]
    if not multithread_func(log, tasks):
        log.error("phone not on 5g nsa")
        return False
    return True


def provision_both_devices_for_wfc_cell_pref(log,
                                             ads,
                                             wifi_ssid,
                                             wifi_pass,
                                             apm_mode=False):
    tasks = [(phone_setup_iwlan,
              (log, ads[0], apm_mode, WFC_MODE_CELLULAR_PREFERRED,
               wifi_ssid, wifi_pass)),
             (phone_setup_iwlan,
              (log, ads[1], apm_mode, WFC_MODE_CELLULAR_PREFERRED,
               wifi_ssid, wifi_pass))]
    if not multithread_func(log, tasks):
        log.error("failed to setup in wfc_cell_pref mode")
        return False
    return True


def provision_both_devices_for_wfc_wifi_pref(log,
                                             ads,
                                             wifi_ssid,
                                             wifi_pass,
                                             apm_mode=False):
    tasks = [(phone_setup_iwlan,
              (log, ads[0], apm_mode, WFC_MODE_WIFI_PREFERRED,
               wifi_ssid, wifi_pass)),
             (phone_setup_iwlan,
              (log, ads[1], apm_mode, WFC_MODE_WIFI_PREFERRED,
               wifi_ssid, wifi_pass))]
    if not multithread_func(log, tasks):
        log.error("failed to setup in wfc_wifi_pref mode")
        return False
    return True


def disable_apm_mode_both_devices(log, ads):
    # Turn off airplane mode
    log.info("Turn off apm mode on both devices")
    tasks = [(toggle_airplane_mode, (log, ads[0], False)),
             (toggle_airplane_mode, (log, ads[1], False))]
    if not multithread_func(log, tasks):
        log.error("Failed to turn off airplane mode")
        return False
    return True


def connect_both_devices_to_wifi(log,
                                 ads,
                                 wifi_ssid,
                                 wifi_pass):
    tasks = [(ensure_wifi_connected, (log, ad, wifi_ssid, wifi_pass))
             for ad in ads]
    if not multithread_func(log, tasks):
        log.error("phone failed to connect to wifi.")
        return False
    return True


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