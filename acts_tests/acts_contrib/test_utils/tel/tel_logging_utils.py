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