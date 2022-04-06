#!/usr/bin/env python3.4
#
#   Copyright 2022 - The Android Open Source Project
#
#   Licensed under the Apache License, Version 2.0 (the 'License');
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an 'AS IS' BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import collections
import logging
import time

PCC_PRESET_MAPPING = {
    'N257': {
        'low': 2054999,
        'mid': 2079165,
        'high': 2090832
    },
    'N258': {
        'low': 2017499,
        'mid': 2043749,
        'high': 2057499
    },
    'N260': {
        'low': 2229999,
        'mid': 2254165,
        'high': 2265832
    },
    'N261': {
        'low': 2071667
    }
}


def extract_test_id(testcase_params, id_fields):
    test_id = collections.OrderedDict(
        (param, testcase_params[param]) for param in id_fields)
    return test_id


def start_pixel_logger(ad):
    """Function to start pixel logger with default log mask.

    Args:
        ad: android device on which to start logger
    """

    try:
        ad.adb.shell(
            'rm -R /storage/emulated/0/Android/data/com.android.pixellogger/files/logs/logs/'
        )
    except:
        pass
    ad.adb.shell(
        'am startservice -a com.android.pixellogger.service.logging.LoggingService.ACTION_START_LOGGING'
    )


def stop_pixel_logger(ad, log_path):
    """Function to stop pixel logger and retrieve logs

    Args:
        ad: android device on which to start logger
        log_path: location of saved logs
    """
    ad.adb.shell(
        'am startservice -a com.android.pixellogger.service.logging.LoggingService.ACTION_STOP_LOGGING'
    )
    logging.info('Waiting for Pixel log file')
    file_name = None
    file_size = 0
    previous_file_size = 0
    for idx in range(600):
        try:
            file = ad.adb.shell(
                'ls -l /storage/emulated/0/Android/data/com.android.pixellogger/files/logs/logs/'
            ).split(' ')
            file_name = file[-1]
            file_size = file[-4]
        except:
            file_name = None
            file_size = 0
        if file_name and file_size == previous_file_size:
            logging.info('Log file found after {}s.'.format(idx))
            break
        else:
            previous_file_size = file_size
            time.sleep(1)
    try:
        ad.pull_files(
            '/storage/emulated/0/Android/data/com.android.pixellogger/files/logs/logs/',
            log_path)
    except:
        logging.error('Could not pull pixel logs.')
