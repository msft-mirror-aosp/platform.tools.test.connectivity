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
import random
import re
import statistics

from acts_contrib.test_utils.tel.tel_subscription_utils import get_slot_index_from_data_sub_id

SETUP_DATA_CALL = 'SETUP_DATA_CALL'
SETUP_DATA_CALL_REQUEST = '> SETUP_DATA_CALL'
SETUP_DATA_CALL_RESPONSE = '< SETUP_DATA_CALL'
IS_CAPTIVEPORTAL = r'isCaptivePortal: isSuccessful()=true'

DEACTIVATE_DATA_CALL = 'DEACTIVATE_DATA_CALL'
DEACTIVATE_DATA_CALL_REQUEST = '> DEACTIVATE_DATA_CALL'
DEACTIVATE_DATA_CALL_RESPONSE = '< DEACTIVATE_DATA_CALL'
UNSOL_DATA_CALL_LIST_CHANGED = 'UNSOL_DATA_CALL_LIST_CHANGED'

IWLAN_DATA_SERVICE = 'IWlanDataService'
IWLAN_SETUP_DATA_CALL_REQUEST = '> REQUEST_SETUP_DATA_CALL'
IWLAN_SETUP_DATA_CALL_RESPONSE = 'setupDataCallResponse'
IWLAN_SEND_ACK = '> send ACK for serial'

IWLAN_DEACTIVATE_DATA_CALL_REQUEST = '> REQUEST_DEACTIVATE_DATA_CALL'
IWLAN_DEACTIVATE_DATA_CALL_RESPONSE = 'deactivateDataCallResponse'

SET_PREFERRED_DATA_MODEM = 'SET_PREFERRED_DATA_MODEM'

WHI_IWLAN_DATA_SERVICE = 'IwlanDataService'
WHI_IWLAN_SETUP_DATA_CALL_REQUEST = r'IwlanDataService\[\d\]: Setup data call'
WHI_IWLAN_SETUP_DATA_CALL_RESPONSE = r'IwlanDataService\[\d\]: Tunnel opened!'
WHI_IWLAN_DEACTIVATE_DATA_CALL_REQUEST = r'IwlanDataService\[\d\]: Deactivate data call'
WHI_IWLAN_DEACTIVATE_DATA_CALL_RESPONSE = r'IwlanDataService\[\d\]: Tunnel closed!'

def print_nested_dict(ad, d):
    divider = "------"
    for k, v in d.items():
        if isinstance(v, dict):
            ad.log.info('%s %s %s', divider, k, divider)
            print_nested_dict(ad, v)
        else:
            ad.log.info('%s: %s', k, v)

def get_slot_from_logcat(msg):
    """Get slot index from specific pattern in logcat

    Args:
        msg: logcat message string

    Returns:
        0 for pSIM or 1 for eSIM
    """
    res = re.findall(r'\[(PHONE[\d])\]', msg)
    try:
        phone = res[0]
    except:
        phone = None
    return phone

def get_apn_from_logcat(msg):
    """Get APN from logcat

    Args:
        msg: logcat message string

    Returns:
        APN
    """
    res = re.findall(r'DataProfile=[^/]+/[^/]+/[^/]+/([^/]+)/', msg)
    try:
        apn = res[0]
    except:
        apn = None
    return apn

def parse_setup_data_call(ad, apn='internet', dds_switch=False):
    """Search in logcat for lines containing data call setup procedure.
        Calculate the data call setup time with given APN and validation
        time on LTE.

    Args:
        ad: Android object
        apn: access point name
        dds_switch: True for switching DDS. Otherwise False.

    Returns:
        setup_data_call: Dictionary containing data call setup request and
            response messages for each data call. The format is shown as
            below:
            {
                message_id:
                {
                    'request':
                    {
                        'message': logcat message body of data call setup
                            request message
                        'time_stamp': time stamp in text format
                        'datetime_obj': datetime object of time stamp
                        'apn': access point name of this request
                        'phone': 0 for pSIM or 1 for eSIM
                    }
                    'response':
                    {
                        'message': logcat message body of data call setup
                            response message
                        'time_stamp': time stamp in text format
                        'datetime_obj': datetime object of time stamp
                        'cause': failure cause if data call setup failed
                        'cid': PDP context ID
                        'ifname': the name of the interface of the network
                        'phone': 0 for pSIM or 1 for eSIM
                        'unsol_data_call_list_changed': message of
                            unsol_data_call_list_changed
                        'unsol_data_call_list_changed_time': time stamp of
                            the message unsol_data_call_list_changed
                        'is_captive_portal': message of LTE validation pass
                        'data_call_setup_time': time between data call setup
                            request and unsol_data_call_list_changed
                        'validation_time_on_lte': time between data call
                            setup response and LTE validation pass
                    }
                }
            }

        data_call_setup_time_list: List. This is a summary of necessary
            messages of data call setup procedure The format is shown as
            below:
                [
                    {
                        'request': logcat message body of data call setup
                            request message
                        'response': logcat message body of data call setup
                            response message
                        'unsol_data_call_list_changed': message of
                            unsol_data_call_list_changed
                        'start': time stamp of data call setup request
                        'end': time stamp of the message
                            unsol_data_call_list_changed
                        'duration': time between data call setup request and
                            unsol_data_call_list_changed
                        'validation_time_on_lte': time between data call
                            setup response and LTE validation pass
                    }
                ]

        avg_data_call_setup_time: average of data call setup time

        avg_validation_time_on_lte: average of time for validation time on
            LTE
    """
    ad.log.info('====== Start to search logcat ====== ')
    logcat = ad.search_logcat(
        r'%s\|%s\|%s\|%s' % (
            SET_PREFERRED_DATA_MODEM,
            SETUP_DATA_CALL,
            UNSOL_DATA_CALL_LIST_CHANGED, IS_CAPTIVEPORTAL))

    if not logcat:
        return False

    for msg in logcat:
        ad.log.info(msg["log_message"])

    dds_slot = get_slot_index_from_data_sub_id(ad)

    set_preferred_data_modem = {}
    setup_data_call = {}
    data_call_setup_time_list = []
    last_message_id = None

    for line in logcat:
        if line['message_id']:
            if SET_PREFERRED_DATA_MODEM in line['log_message']:
                set_preferred_data_modem['message'] = line['log_message']
                set_preferred_data_modem['time_stamp'] = line['time_stamp']
                set_preferred_data_modem[
                    'datetime_obj'] = line['datetime_obj']

            if SETUP_DATA_CALL_REQUEST in line['log_message']:
                found_apn = get_apn_from_logcat(line['log_message'])
                if found_apn != apn:
                    continue

                phone = get_slot_from_logcat(line['log_message'])
                if not phone:
                    continue

                if not dds_switch:
                    if str(dds_slot) not in phone:
                        continue

                msg_id = line['message_id']
                last_message_id = line['message_id']
                if msg_id not in setup_data_call:
                    setup_data_call[msg_id] = {}

                setup_data_call[msg_id]['request'] = {
                    'message': line['log_message'],
                    'time_stamp': line['time_stamp'],
                    'datetime_obj': line['datetime_obj'],
                    'apn': found_apn,
                    'phone': phone}

                if set_preferred_data_modem:
                    setup_data_call[msg_id]['request'][
                        'set_preferred_data_modem_message'] = set_preferred_data_modem['message']
                    setup_data_call[msg_id]['request'][
                        'set_preferred_data_modem_time_stamp'] = set_preferred_data_modem['time_stamp']
                    setup_data_call[msg_id]['request'][
                        'set_preferred_data_modem_datetime_obj'] = set_preferred_data_modem['datetime_obj']
                    set_preferred_data_modem = {}

            if SETUP_DATA_CALL_RESPONSE in line['log_message']:
                phone = get_slot_from_logcat(line['log_message'])
                if not phone:
                    continue

                if not dds_switch:
                    if str(dds_slot) not in phone:
                        continue

                msg_id = line['message_id']
                if msg_id not in setup_data_call:
                    continue

                if 'request' not in setup_data_call[msg_id]:
                    continue

                last_message_id = line['message_id']

                setup_data_call[msg_id]['response'] = {
                    'message': line['log_message'],
                    'time_stamp': line['time_stamp'],
                    'datetime_obj': line['datetime_obj'],
                    'cause': '0',
                    'cid': None,
                    'ifname': None,
                    'phone': phone,
                    'unsol_data_call_list_changed': None,
                    'unsol_data_call_list_changed_time': None,
                    'is_captive_portal': None,
                    'data_call_setup_time': None,
                    'validation_time_on_lte': None}

                res = re.findall(r'cause=(\d+)', line['log_message'])
                try:
                    cause = res[0]
                    setup_data_call[msg_id]['response']['cause'] = cause
                except:
                    pass

                res = re.findall(r'cid=(\d+)', line['log_message'])
                try:
                    cid = res[0]
                    setup_data_call[msg_id]['response']['cid'] = cid
                except:
                    pass

                res = re.findall(r'ifname=(\S+)', line['log_message'])
                try:
                    ifname = res[0]
                    setup_data_call[msg_id]['response']['ifname'] = ifname
                except:
                    pass

        if UNSOL_DATA_CALL_LIST_CHANGED in line['log_message']:
            if not last_message_id:
                continue

            phone = get_slot_from_logcat(line['log_message'])
            if not phone:
                continue

            if not dds_switch:
                if str(dds_slot) not in phone:
                    continue

            if 'request' not in setup_data_call[last_message_id]:
                continue

            if 'response' not in setup_data_call[last_message_id]:
                continue

            cid =  setup_data_call[last_message_id]['response']['cid']
            if 'cid = %s' % cid not in line['log_message']:
                continue

            if setup_data_call[last_message_id]['response']['cause'] != '0':
                continue

            if dds_switch:
                if 'set_preferred_data_modem_message' not in setup_data_call[
                    last_message_id]['request']:
                    continue
                data_call_start_time = setup_data_call[last_message_id][
                    'request']['set_preferred_data_modem_datetime_obj']

            else:
                data_call_start_time = setup_data_call[last_message_id][
                    'request']['datetime_obj']

            data_call_end_time = line['datetime_obj']
            setup_data_call[last_message_id]['response'][
                'unsol_data_call_list_changed_time'] = data_call_end_time
            setup_data_call[last_message_id]['response'][
                'unsol_data_call_list_changed'] = line['log_message']
            data_call_setup_time = data_call_end_time - data_call_start_time
            setup_data_call[last_message_id]['response'][
                'data_call_setup_time'] = data_call_setup_time.total_seconds()

            if apn == 'ims':
                data_call_setup_time_list.append(
                    {'request': setup_data_call[
                        last_message_id]['request']['message'],
                    'response': setup_data_call[
                        last_message_id]['response']['message'],
                    'unsol_data_call_list_changed': setup_data_call[
                        last_message_id]['response'][
                            'unsol_data_call_list_changed'],
                    'start': data_call_start_time,
                    'end': data_call_end_time,
                    'duration': setup_data_call[last_message_id]['response'][
                        'data_call_setup_time']})

                last_message_id = None

        if IS_CAPTIVEPORTAL in line['log_message']:
            if not last_message_id:
                continue

            if 'request' not in setup_data_call[last_message_id]:
                continue

            if 'response' not in setup_data_call[last_message_id]:
                continue

            if dds_switch:
                data_call_start_time = setup_data_call[last_message_id][
                    'request']['set_preferred_data_modem_datetime_obj']

            else:
                data_call_start_time = setup_data_call[last_message_id][
                    'request']['datetime_obj']

            setup_data_call[last_message_id]['response'][
                'is_captive_portal'] = line['log_message']
            validation_start_time_on_lte = setup_data_call[
                last_message_id]['response']['datetime_obj']
            validation_end_time_on_lte = line['datetime_obj']
            validation_time_on_lte = (
                validation_end_time_on_lte - validation_start_time_on_lte).total_seconds()
            setup_data_call[last_message_id]['response'][
                'validation_time_on_lte'] = validation_time_on_lte

            data_call_setup_time_list.append(
                {'request': setup_data_call[last_message_id]['request'][
                    'message'],
                'response': setup_data_call[last_message_id]['response'][
                    'message'],
                'unsol_data_call_list_changed': setup_data_call[
                    last_message_id]['response']['unsol_data_call_list_changed'],
                'start': data_call_start_time,
                'end': setup_data_call[last_message_id]['response'][
                    'unsol_data_call_list_changed_time'],
                'duration': setup_data_call[last_message_id]['response'][
                    'data_call_setup_time'],
                'validation_time_on_lte': validation_time_on_lte})

            last_message_id = None

    duration_list = []
    for item in data_call_setup_time_list:
        if 'duration' in item:
            duration_list.append(item['duration'])

    try:
        avg_data_call_setup_time = statistics.mean(duration_list)
    except:
        avg_data_call_setup_time = None

    validation_time_on_lte_list = []
    for item in data_call_setup_time_list:
        if 'validation_time_on_lte' in item:
            validation_time_on_lte_list.append(
                item['validation_time_on_lte'])

    try:
        avg_validation_time_on_lte = statistics.mean(
            validation_time_on_lte_list)
    except:
        avg_validation_time_on_lte = None

    return (
        setup_data_call,
        data_call_setup_time_list,
        avg_data_call_setup_time,
        avg_validation_time_on_lte)

def parse_setup_data_call_on_iwlan(ad):
    """Search in logcat for lines containing data call setup procedure.
        Calculate the data call setup time with given APN on iwlan.

    Args:
        ad: Android object
        apn: access point name

    Returns:
        setup_data_call: Dictionary containing data call setup request and
            response messages for each data call. The format is shown as
            below:
            {
                message_id:
                {
                    'request':
                    {
                        'message': logcat message body of data call setup
                            request message
                        'time_stamp': time stamp in text format
                        'datetime_obj': datetime object of time stamp
                    }
                    'response':
                    {
                        'message': logcat message body of data call setup
                            response message
                        'time_stamp': time stamp in text format
                        'datetime_obj': datetime object of time stamp
                        'cause': failure cause if data call setup failed
                        'data_call_setup_time': time between data call setup
                            request and response
                    }
                }
            }

        data_call_setup_time_list:
            List. This is a summary of mecessary messages of data call setup
                procedure The format is shown as below:
                [
                    {
                        'request': logcat message body of data call setup
                            request message
                        'response': logcat message body of data call setup
                            response message
                        'start': time stamp of data call setup request
                        'end': time stamp of data call setup response
                        'duration': time between data call setup request and
                            response
                    }
                ]

        avg_data_call_setup_time: average of data call setup time
    """
    ad.log.info('====== Start to search logcat ====== ')
    logcat = ad.search_logcat(r'%s\|%s' % (
        IWLAN_DATA_SERVICE, WHI_IWLAN_DATA_SERVICE))

    found_iwlan_data_service = 1
    if not logcat:
        found_iwlan_data_service = 0

    if not found_iwlan_data_service:
        (
            setup_data_call,
            data_call_setup_time_list,
            avg_data_call_setup_time,
            _) = parse_setup_data_call(ad, apn='ims')

        return (
            setup_data_call,
            data_call_setup_time_list,
            avg_data_call_setup_time)

    for msg in logcat:
        ad.log.info(msg["log_message"])

    setup_data_call = {}
    data_call_setup_time_list = []
    last_message_id = None

    whi_msg_index = None
    for line in logcat:
        serial = None
        cause = None
        if IWLAN_SETUP_DATA_CALL_REQUEST in line['log_message']:
            match_res = re.findall(
                r'%s:\s(\d+)' % IWLAN_DATA_SERVICE, line['log_message'])
            if match_res:
                try:
                    serial = match_res[0]
                except:
                    pass

            if not serial:
                continue

            msg_id = serial
            last_message_id = serial
            if msg_id not in setup_data_call:
                setup_data_call[msg_id] = {}

            setup_data_call[msg_id]['request'] = {
                'message': line['log_message'],
                'time_stamp': line['time_stamp'],
                'datetime_obj': line['datetime_obj']}

        else:
            if re.search(
                WHI_IWLAN_SETUP_DATA_CALL_REQUEST, line['log_message']):
                if whi_msg_index is None:
                    whi_msg_index = 0
                else:
                    whi_msg_index = whi_msg_index + 1

                if str(whi_msg_index) not in setup_data_call:
                    setup_data_call[str(whi_msg_index)] = {}

                setup_data_call[str(whi_msg_index)]['request'] = {
                    'message': line['log_message'],
                    'time_stamp': line['time_stamp'],
                    'datetime_obj': line['datetime_obj']}

        if IWLAN_SETUP_DATA_CALL_RESPONSE in line['log_message']:
            match_res = re.findall(r'Serial = (\d+)', line['log_message'])
            if match_res:
                try:
                    serial = match_res[0]
                except:
                    pass

            if serial:
                msg_id = serial
            else:
                msg_id = last_message_id

            if msg_id not in setup_data_call:
                continue

            if 'request' not in setup_data_call[msg_id]:
                continue

            setup_data_call[msg_id]['response'] = {
                'message': None,
                'time_stamp': None,
                'datetime_obj': None,
                'cause': None,
                'data_call_setup_time': None}

            match_res = re.findall(
                r'Fail Cause = (\d+)', line['log_message'])
            if match_res:
                try:
                    cause = match_res[0]
                except:
                    cause = None

            if cause != '0':
                continue

            setup_data_call[msg_id]['response']['message'] = line[
                'log_message']
            setup_data_call[msg_id]['response']['time_stamp'] = line[
                'time_stamp']
            setup_data_call[msg_id]['response']['datetime_obj'] = line[
                'datetime_obj']
            setup_data_call[msg_id]['response']['cause'] = 0

            data_call_start_time = setup_data_call[last_message_id][
                'request']['datetime_obj']
            data_call_end_time = line['datetime_obj']
            data_call_setup_time = data_call_end_time - data_call_start_time
            setup_data_call[last_message_id]['response'][
                'data_call_setup_time'] = data_call_setup_time.total_seconds()

            data_call_setup_time_list.append(
                {'request': setup_data_call[last_message_id]['request'][
                    'message'],
                'response': setup_data_call[last_message_id]['response'][
                    'message'],
                'start': setup_data_call[last_message_id]['request'][
                    'datetime_obj'],
                'end': setup_data_call[last_message_id]['response'][
                    'datetime_obj'],
                'duration': setup_data_call[last_message_id]['response'][
                    'data_call_setup_time']})

            last_message_id = None

        else:
            if re.search(
                WHI_IWLAN_SETUP_DATA_CALL_RESPONSE, line['log_message']):
                if whi_msg_index is None:
                    continue

                if 'response' in setup_data_call[str(whi_msg_index)]:
                    ad.log.error('Duplicated setup data call response is '
                    'found or the request message is lost.')
                    continue

                setup_data_call[str(whi_msg_index)]['response'] = {
                    'message': line['log_message'],
                    'time_stamp': line['time_stamp'],
                    'datetime_obj': line['datetime_obj'],
                    'data_call_setup_time': None}

                data_call_start_time = setup_data_call[str(whi_msg_index)][
                    'request']['datetime_obj']
                data_call_end_time = line['datetime_obj']
                data_call_setup_time = data_call_end_time - data_call_start_time
                setup_data_call[str(whi_msg_index)]['response'][
                    'data_call_setup_time'] = data_call_setup_time.total_seconds()

                data_call_setup_time_list.append(
                    {'request': setup_data_call[str(whi_msg_index)][
                        'request']['message'],
                    'response': setup_data_call[str(whi_msg_index)][
                        'response']['message'],
                    'start': setup_data_call[str(whi_msg_index)]['request'][
                        'datetime_obj'],
                    'end': setup_data_call[str(whi_msg_index)]['response'][
                        'datetime_obj'],
                    'duration': setup_data_call[str(whi_msg_index)][
                        'response']['data_call_setup_time']})

    duration_list = []
    for item in data_call_setup_time_list:
        if 'duration' in item:
            duration_list.append(item['duration'])

    try:
        avg_data_call_setup_time = statistics.mean(duration_list)
    except:
        avg_data_call_setup_time = None

    ad.log.warning('setup_data_call: %s', setup_data_call)
    ad.log.warning('duration list: %s', duration_list)
    ad.log.warning('avg_data_call_setup_time: %s', avg_data_call_setup_time)

    return (
        setup_data_call,
        data_call_setup_time_list,
        avg_data_call_setup_time)

def parse_deactivate_data_call(ad):
    """Search in logcat for lines containing data call deactivation procedure.
        Calculate the data call deactivation time on LTE.

    Args:
        ad: Android object

    Returns:
        deactivate_data_call: Dictionary containing data call deactivation
            request and response messages for each data call. The format is
            shown as below:
            {
                message_id:
                {
                    'request':
                    {
                        'message': logcat message body of data call
                            deactivation request message
                        'time_stamp': time stamp in text format
                        'datetime_obj': datetime object of time stamp
                        'cid': PDP context ID
                        'phone': 0 for pSIM or 1 for eSIM
                    }
                    'response':
                    {
                        'message': logcat message body of data call
                            deactivation response message
                        'time_stamp': time stamp in text format
                        'datetime_obj': datetime object of time stamp
                        'phone': 0 for pSIM or 1 for eSIM
                        'unsol_data_call_list_changed': message of
                            unsol_data_call_list_changed
                        'deactivate_data_call_time': time between data call
                            deactivation request and unsol_data_call_list_changed
                    }
                }
            }

        deactivate_data_call_time_list: List. This is a summary of necessary
            messages of data call deactivation procedure The format is shown
            as below:
                [
                    {
                        'request': logcat message body of data call
                            deactivation request message
                        'response': logcat message body of data call
                            deactivation response message
                        'unsol_data_call_list_changed': message of
                            unsol_data_call_list_changed
                        'start': time stamp of data call deactivation request
                        'end': time stamp of the message
                            unsol_data_call_list_changed
                        'duration': time between data call deactivation
                            request and unsol_data_call_list_changed
                    }
                ]

        avg_deactivate_data_call_time: average of data call deactivation time
    """
    ad.log.info('====== Start to search logcat ====== ')
    logcat = ad.search_logcat(
        r'%s\|%s' % (DEACTIVATE_DATA_CALL, UNSOL_DATA_CALL_LIST_CHANGED))
    if not logcat:
        return False

    for msg in logcat:
        ad.log.info(msg["log_message"])

    dds_slot = get_slot_index_from_data_sub_id(ad)

    deactivate_data_call = {}
    deactivate_data_call_time_list = []
    last_message_id = None

    for line in logcat:
        if line['message_id']:
            if DEACTIVATE_DATA_CALL_REQUEST in line['log_message']:
                phone = get_slot_from_logcat(line['log_message'])
                if not phone:
                    continue

                if str(dds_slot) not in phone:
                    continue

                msg_id = line['message_id']
                last_message_id = line['message_id']
                if msg_id not in deactivate_data_call:
                    deactivate_data_call[msg_id] = {}

                deactivate_data_call[msg_id]['request'] = {
                    'message': line['log_message'],
                    'time_stamp': line['time_stamp'],
                    'datetime_obj': line['datetime_obj'],
                    'cid': None,
                    'phone': dds_slot}

                res = re.findall(r'cid = (\d+)', line['log_message'])
                try:
                    cid = res[0]
                    deactivate_data_call[msg_id]['request']['cid'] = cid
                except:
                    pass

            if DEACTIVATE_DATA_CALL_RESPONSE in line['log_message']:
                phone = get_slot_from_logcat(line['log_message'])
                if not phone:
                    continue

                if str(dds_slot) not in phone:
                    continue

                msg_id = line['message_id']
                if msg_id not in deactivate_data_call:
                    continue

                if 'request' not in deactivate_data_call[msg_id]:
                    continue

                last_message_id = line['message_id']

                deactivate_data_call[msg_id]['response'] = {
                    'message': line['log_message'],
                    'time_stamp': line['time_stamp'],
                    'datetime_obj': line['datetime_obj'],
                    'phone': dds_slot,
                    'unsol_data_call_list_changed': None,
                    'deactivate_data_call_time': None}

        if UNSOL_DATA_CALL_LIST_CHANGED in line['log_message']:
            if not last_message_id:
                continue

            phone = get_slot_from_logcat(line['log_message'])
            if not phone:
                continue

            if str(dds_slot) not in phone:
                continue

            if 'request' not in deactivate_data_call[last_message_id]:
                continue

            if 'response' not in deactivate_data_call[last_message_id]:
                continue

            cid = deactivate_data_call[last_message_id]['request']['cid']
            if 'cid = %s' % cid not in line['log_message']:
                continue

            deactivate_data_call_start_time = deactivate_data_call[
                last_message_id]['request']['datetime_obj']
            deactivate_data_call_end_time = line['datetime_obj']
            deactivate_data_call[last_message_id]['response'][
                'unsol_data_call_list_changed'] = line['log_message']
            deactivate_data_call_time = (
                deactivate_data_call_end_time - deactivate_data_call_start_time)
            deactivate_data_call[last_message_id]['response'][
                'deactivate_data_call_time'] = deactivate_data_call_time.total_seconds()
            deactivate_data_call_time_list.append(
                {'request': deactivate_data_call[last_message_id][
                    'request']['message'],
                'response': deactivate_data_call[last_message_id][
                    'response']['message'],
                'unsol_data_call_list_changed': deactivate_data_call[
                    last_message_id]['response'][
                        'unsol_data_call_list_changed'],
                'start': deactivate_data_call_start_time,
                'end': deactivate_data_call_end_time,
                'duration': deactivate_data_call_time.total_seconds()})

            last_message_id = None

    duration_list = []
    for item in deactivate_data_call_time_list:
        if 'duration' in item:
            duration_list.append(item['duration'])

    try:
        avg_deactivate_data_call_time = statistics.mean(duration_list)
    except:
        avg_deactivate_data_call_time = None

    return (
        deactivate_data_call,
        deactivate_data_call_time_list,
        avg_deactivate_data_call_time)

def parse_deactivate_data_call_on_iwlan(ad):
    """Search in logcat for lines containing data call deactivation procedure.
        Calculate the data call deactivation time on iwlan.

    Args:
        ad: Android object

    Returns:
        deactivate_data_call: Dictionary containing data call deactivation
            request and response messages for each data call. The format is
            shown as below:
            {
                message_id:
                {
                    'request':
                    {
                        'message': logcat message body of data call
                            deactivation request message
                        'time_stamp': time stamp in text format
                        'datetime_obj': datetime object of time stamp
                    }
                    'response':
                    {
                        'message': logcat message body of data call
                            deactivation response message
                        'time_stamp': time stamp in text format
                        'datetime_obj': datetime object of time stamp
                        'send_ack_for_serial_time': time stamp of ACK
                        'deactivate_data_call_time': time between data call
                            deactivation request and ACK
                    }
                }
            }

        deactivate_data_call_time_list: List. This is a summary of necessary
            messages of data call deactivation procedure The format is shown
            as below:
                [
                    {
                        'request': logcat message body of data call
                            deactivation request message
                        'response': logcat message body of data call
                            deactivation response message
                        'start': time stamp of data call deactivation request
                        'end': time stamp of the ACK
                        'duration': time between data call deactivation
                            request and ACK
                    }
                ]

        avg_deactivate_data_call_time: average of data call deactivation time
    """
    ad.log.info('====== Start to search logcat ====== ')
    logcat = ad.search_logcat(r'%s\|%s' % (
        IWLAN_DATA_SERVICE, WHI_IWLAN_DATA_SERVICE))

    found_iwlan_data_service = 1
    if not logcat:
        found_iwlan_data_service = 0

    if not found_iwlan_data_service:
        (
            deactivate_data_call,
            deactivate_data_call_time_list,
            avg_deactivate_data_call_time) = parse_deactivate_data_call(ad)

        return (
            deactivate_data_call,
            deactivate_data_call_time_list,
            avg_deactivate_data_call_time)

    for msg in logcat:
        ad.log.info(msg["log_message"])

    deactivate_data_call = {}
    deactivate_data_call_time_list = []
    last_message_id = None

    whi_msg_index = None
    for line in logcat:
        serial = None
        if IWLAN_DEACTIVATE_DATA_CALL_REQUEST in line['log_message']:
            match_res = re.findall(
                r'%s:\s(\d+)' % IWLAN_DATA_SERVICE, line['log_message'])
            if match_res:
                try:
                    serial = match_res[0]
                except:
                    serial = None

            if not serial:
                continue

            msg_id = serial
            last_message_id = serial
            if msg_id not in deactivate_data_call:
                deactivate_data_call[msg_id] = {}

            deactivate_data_call[msg_id]['request'] = {
                'message': line['log_message'],
                'time_stamp': line['time_stamp'],
                'datetime_obj': line['datetime_obj']}
        else:
            if re.search(WHI_IWLAN_DEACTIVATE_DATA_CALL_REQUEST, line[
                'log_message']):
                if whi_msg_index is None:
                    whi_msg_index = 0
                else:
                    whi_msg_index = whi_msg_index + 1

                if str(whi_msg_index) not in deactivate_data_call:
                    deactivate_data_call[str(whi_msg_index)] = {}

                deactivate_data_call[str(whi_msg_index)]['request'] = {
                    'message': line['log_message'],
                    'time_stamp': line['time_stamp'],
                    'datetime_obj': line['datetime_obj']}

        if IWLAN_DEACTIVATE_DATA_CALL_RESPONSE in line['log_message']:
            if 'response' not in deactivate_data_call[last_message_id]:
                deactivate_data_call[msg_id]['response'] = {}

            deactivate_data_call[msg_id]['response'] = {
                'message': line['log_message'],
                'time_stamp': line['time_stamp'],
                'datetime_obj': line['datetime_obj'],
                'send_ack_for_serial_time': None,
                'deactivate_data_call_time': None}

        else:
            if re.search(WHI_IWLAN_DEACTIVATE_DATA_CALL_RESPONSE, line[
                'log_message']):
                if whi_msg_index is None:
                    continue

                if 'response' in deactivate_data_call[str(whi_msg_index)]:
                    ad.log.error('Duplicated deactivate data call response'
                    'is found or the request message is lost.')
                    continue

                deactivate_data_call[str(whi_msg_index)]['response'] = {
                    'message': line['log_message'],
                    'time_stamp': line['time_stamp'],
                    'datetime_obj': line['datetime_obj'],
                    'deactivate_data_call_time': None}

                deactivate_data_call_start_time = deactivate_data_call[
                    str(whi_msg_index)]['request']['datetime_obj']
                deactivate_data_call_end_time = line['datetime_obj']
                deactivate_data_call_time = (
                    deactivate_data_call_end_time - deactivate_data_call_start_time)
                deactivate_data_call[str(whi_msg_index)]['response'][
                    'deactivate_data_call_time'] = deactivate_data_call_time.total_seconds()
                deactivate_data_call_time_list.append(
                    {'request': deactivate_data_call[str(whi_msg_index)][
                        'request']['message'],
                    'response': deactivate_data_call[str(whi_msg_index)][
                        'response']['message'],
                    'start': deactivate_data_call_start_time,
                    'end': deactivate_data_call_end_time,
                    'duration': deactivate_data_call_time.total_seconds()})

        if IWLAN_SEND_ACK in line['log_message']:
            match_res = re.findall(
                r'%s:\s(\d+)' % IWLAN_DATA_SERVICE, line['log_message'])
            if match_res:
                try:
                    serial = match_res[0]
                except:
                    serial = None

            if not serial:
                continue

            msg_id = serial

            if msg_id not in deactivate_data_call:
                continue

            if 'response' not in deactivate_data_call[msg_id]:
                continue

            deactivate_data_call[msg_id]['response'][
                'send_ack_for_serial_time'] = line['datetime_obj']

            deactivate_data_call_start_time = deactivate_data_call[msg_id][
                'request']['datetime_obj']
            deactivate_data_call_end_time = line['datetime_obj']
            deactivate_data_call_time = (
                deactivate_data_call_end_time - deactivate_data_call_start_time)
            deactivate_data_call[msg_id]['response'][
                'deactivate_data_call_time'] = deactivate_data_call_time.total_seconds()
            deactivate_data_call_time_list.append(
                {'request': deactivate_data_call[msg_id]['request'][
                    'message'],
                'response': deactivate_data_call[msg_id]['response'][
                    'message'],
                'start': deactivate_data_call_start_time,
                'end': deactivate_data_call_end_time,
                'duration': deactivate_data_call_time.total_seconds()})

            last_message_id = None

    duration_list = []
    for item in deactivate_data_call_time_list:
        if 'duration' in item:
            duration_list.append(item['duration'])

    try:
        avg_deactivate_data_call_time = statistics.mean(duration_list)
    except:
        avg_deactivate_data_call_time = None

    return (
        deactivate_data_call,
        deactivate_data_call_time_list,
        avg_deactivate_data_call_time)