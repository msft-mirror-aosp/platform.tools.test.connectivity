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

from acts.controllers.android_device import DEFAULT_SDM_LOG_PATH
from acts_contrib.test_utils.tel.tel_test_utils import run_multithread_func

def check_if_tensor_platform(ad):
    """Check if current platform belongs to the Tensor platform

    Args:
        ad: Android object

    Returns:
        True if current platform belongs to the Tensor platform. Otherwise False.
    """
    result = ad.adb.getprop("ro.boot.hardware.platform")
    if re.search('^gs', result, re.I):
        return True
    return False

def start_pixellogger_always_on_logging(ad):
    """Start always-on logging of Pixellogger for both Qualcomm and Tensor
    platform.

    Args:
        ad: Android object

    Returns:
        True if the property is set correctly. Otherwise False.
    """
    setattr(ad, 'enable_always_on_modem_logger', True)
    if check_if_tensor_platform(ad):
        key = "persist.vendor.sys.modem.logging.enable"
    else:
        key = "persist.vendor.sys.modem.diag.mdlog"

    if ad.adb.getprop(key) == "false":
        ad.adb.shell("setprop persist.vendor.sys.modem.logging.enable true")
        time.sleep(5)
        if ad.adb.getprop(key) == "true":
            return True
        else:
            return False
    else:
        return True

def start_sdm_logger(ad):
    """Start SDM logger."""
    if not getattr(ad, "sdm_log", True): return
    # Delete existing SDM logs which were created 15 mins prior
    ad.sdm_log_path = DEFAULT_SDM_LOG_PATH
    file_count = ad.adb.shell(
        "find %s -type f -iname sbuff_[0-9]*.sdm* | wc -l" % ad.sdm_log_path)
    if int(file_count) > 3:
        seconds = 15 * 60
        # Remove sdm logs modified more than specified seconds ago
        ad.adb.shell(
            "find %s -type f -iname sbuff_[0-9]*.sdm* -not -mtime -%ss -delete" %
            (ad.sdm_log_path, seconds))
    # Disable any modem logging already running
    if not getattr(ad, "enable_always_on_modem_logger", False):
        ad.adb.shell("setprop persist.vendor.sys.modem.logging.enable false")
    # start logging
    cmd = "setprop vendor.sys.modem.logging.enable true"
    ad.log.debug("start sdm logging")
    ad.adb.shell(cmd, ignore_status=True)
    time.sleep(5)

def stop_sdm_logger(ad):
    """Stop SDM logger."""
    cmd = "setprop vendor.sys.modem.logging.enable false"
    ad.log.debug("stop sdm logging")
    ad.adb.shell(cmd, ignore_status=True)
    time.sleep(5)

def start_sdm_loggers(log, ads):
    tasks = [(start_sdm_logger, [ad]) for ad in ads
             if getattr(ad, "sdm_log", True)]
    if tasks: run_multithread_func(log, tasks)

def stop_sdm_loggers(log, ads):
    tasks = [(stop_sdm_logger, [ad]) for ad in ads]
    run_multithread_func(log, tasks)