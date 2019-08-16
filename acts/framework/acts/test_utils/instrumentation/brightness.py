#!/usr/bin/env python3
#
#   Copyright 2019 - The Android Open Source Project
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

_BRIGHTNESS_FOR_200_NITS = {
    'hammerhead': 88,
    'shamu': 203,
    'razor': 112,  # Flo
    'razorg': 112,  # Deb
    'volantis': 175,
    'volantisg': 175,
    '4560MMX': 155,  # Tinno
    '4560MMX_b': 164,  # Longcheer
    'AQ4501': 120,  # Tinno MicroMax
    'Mi-498': 134,  # Sprout Spice
    'l8150': 113,  # Seed
    'ctih220': 116,  # Seed Cherry
    'angler': 158,  # Angler
    'bullhead': 149,  # Bullhead
    'ryu': 91,  # Ryu
    'sailfish': 131,  # Sailfish & friends
    'sailfish_eas': 131,
    'sailfish_vboot': 131,
    'marlin': 147,  # Marlin & friends
    'marlin_eas': 147,
    'muskie': 152,  # Muskie
    'vega': 156,  # Vega day dream device
    'walleye': 136,  # Walleye & friends
    'walleye_clang': 136,
    'walleye_kcfi': 136,
    'walleye_vboot': 136,
    'taimen': 157,  # Taimen & friends
    'taimen_clang': 157,
    'crosshatch': 130,  # Crosshatch
    'blueline': 114,  # Blueline
    'bonito': 120,  # Bonito
    'sargo': 126,  # Sargo
    'maran9810': 130,  # Maran9810
    'maran9820': 130,  # Maran9820
    'maran9820_419': 130,  # Maran9820_419
    'coral': 123,  # Coral
    'flame': 118,  # Flame
}

_BRIGHTNESS_FOR_100_LUX = {
    'sailfish': 48,  # Sailfish & friends
    'marlin': 57,  # Marlin & friends
    'walleye': 40,  # Walleye & friends
    'taimen': 55,  # Taimen & friends
    'crosshatch': 60,  # Crosshatch
    'blueline': 61,  # Blueline
    'bonito': 54,  # Bonito
    'sargo': 54,  # Sargo
    'maran9810': 60,  # Maran9810
    'coral': 67,  # Coral
    'flame': 58,  # Flame
}


def get_brightness_for_200_nits(model_name):
    """Returns the brightness setting for 200 nits on the specified model."""
    return _BRIGHTNESS_FOR_200_NITS[model_name]


def get_brightness_for_100_lux(model_name):
    """Returns the brightness setting for 100 lux on the specified model."""
    return _BRIGHTNESS_FOR_100_LUX[model_name]
