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

from queue import Empty
from acts_contrib.test_utils.tel.tel_defines import OverrideNetworkContainer
from acts_contrib.test_utils.tel.tel_defines import DisplayInfoContainer
from acts_contrib.test_utils.tel.tel_defines import EventDisplayInfoChanged

def is_current_network_5g_nsa(ad, nr_type=None, timeout=30):
    """Verifies 5G NSA override network type
    Args:
        ad: android device object.
        nr_type: 'nsa' for 5G non-standalone, 'mmwave' for 5G millimeter
                wave
        timeout: max time to wait for event.

    Returns:
        True: if data is on nsa5g NSA
        False: if data is not on nsa5g NSA
    """
    ad.ed.clear_events(EventDisplayInfoChanged)
    ad.droid.telephonyStartTrackingDisplayInfoChange()
    if nr_type == 'mmwave':
        nsa_band = OverrideNetworkContainer.OVERRIDE_NETWORK_TYPE_NR_MMWAVE
    elif nr_type == 'nsa':
        nsa_band = OverrideNetworkContainer.OVERRIDE_NETWORK_TYPE_NR_NSA
    else:
        nsa_band = OverrideNetworkContainer.OVERRIDE_NETWORK_TYPE_NR_NSA
    try:
        event = ad.ed.wait_for_event(
                EventDisplayInfoChanged,
                ad.ed.is_event_match,
                timeout=timeout,
                field=DisplayInfoContainer.OVERRIDE,
                value=nsa_band)
        ad.log.info("Got expected event %s", event)
        return True
    except Empty:
        ad.log.info("No event for display info change")
        ad.screenshot("5g_nsa_icon_checking")
        return False
    finally:
        ad.droid.telephonyStopTrackingDisplayInfoChange()
    return None


def is_current_network_5g_nsa_for_subscription(ad, nr_type=None, timeout=30, sub_id=None):
    """Verifies 5G NSA override network type for subscription id.
    Args:
        ad: android device object.
        nr_type: 'nsa' for 5G non-standalone, 'mmwave' for 5G millimeter wave
        timeout: max time to wait for event.
        sub_id: subscription id.

    Returns:
        True: if data is on nsa5g NSA
        False: if data is not on nsa5g NSA
    """
    if not sub_id:
        return is_current_network_5g_nsa(ad, nr_type=nr_type)

    voice_sub_id_changed = False
    current_sub_id = ad.droid.subscriptionGetDefaultVoiceSubId()
    if current_sub_id != sub_id:
        ad.droid.subscriptionSetDefaultVoiceSubId(sub_id)
        voice_sub_id_changed = True

    result = is_current_network_5g_nsa(ad, nr_type=nr_type)

    if voice_sub_id_changed:
        ad.droid.subscriptionSetDefaultVoiceSubId(current_sub_id)

    return result


def is_current_network_5g_sa(ad):
    """Verifies 5G SA override network type

    Args:
        ad: android device object.

    Returns:
        True: if data is on 5g SA
        False: if data is not on 5g SA
    """
    network_connected = ad.droid.telephonyGetCurrentDataNetworkType()
    if network_connected == 'NR':
        ad.log.debug("Network is currently connected to %s", network_connected)
        return True
    else:
        ad.log.error("Network is currently connected to %s, Expected on NR", network_connected)
        ad.screenshot("5g_sa_icon_checking")
        return False


def is_current_network_5g(ad, nr_type=None, timeout=30):
    """Verifies 5G override network type

    Args:
        ad: android device object
        nr_type: 'sa' for 5G standalone, 'nsa' for 5G non-standalone, 'mmwave' for 5G millimeter
                wave
        timeout: max time to wait for event.

    Returns:
        True: if data is on 5G regardless of SA or NSA
        False: if data is not on 5G refardless of SA or NSA
    """
    if nr_type == 'nsa':
        return is_current_network_5g_nsa(ad, nr_type = 'nsa', timeout=timeout)
    elif nr_type == 'sa':
        return is_current_network_5g_sa(ad)
    elif nr_type == 'mmwave':
        return is_current_network_5g_nsa(ad, nr_type = 'mmwave', timeout=timeout)
    else:
        return is_current_network_5g_nsa(ad, nr_type=None) or is_current_network_5g_sa(ad)


def is_current_network_5g_for_subscription(ad, sub_id=None, nr_type=None):
    """Verifies 5G override network type for subscription id.
    Args:
        ad: android device object
        sub_id: subscription id
        nr_type: 'sa' for 5G standalone, 'nsa' for 5G non-standalone, 'mmwave' for 5G millimeter
                wave

    Returns:
        True: if data is on 5G regardless of NSA or SA.
        False: if data is not on 5G regardless of NSA or SA.
    """
    if not sub_id:
        return is_current_network_5g(ad, nr_type=nr_type)

    voice_sub_id_changed = False
    current_sub_id = ad.droid.subscriptionGetDefaultVoiceSubId()
    if current_sub_id != sub_id:
        ad.droid.subscriptionSetDefaultVoiceSubId(sub_id)
        voice_sub_id_changed = True

    result = is_current_network_5g(ad, nr_type=nr_type)

    if voice_sub_id_changed:
        ad.droid.subscriptionSetDefaultVoiceSubId(current_sub_id)

    return result
