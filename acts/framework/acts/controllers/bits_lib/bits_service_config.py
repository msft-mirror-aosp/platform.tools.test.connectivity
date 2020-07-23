#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
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

import copy

DEFAULT_MONSOON_CONFIG_DICT = {
    'enabled': 1,
    'type': 'monsooncollector',
    'monsoon_reset': 0,
    # maximum monsoon sample rate that works best for both lvpm and hvpm
    'sampling_rate': 4000,
}


class _BitsMonsoonConfig(object):
    """Helper object to construct a bits_service config from a monsoon config as
    defined for the bits controller config and required additional resources,
    such as paths to executables.

    The format for the bits_service's monsoon configuration is explained at:
    http://go/pixel-bits/user-guide/service/collectors/monsoon

    Attributes:
        config_dic: A bits_service's monsoon configuration as a python
        dictionary.
    """

    def __init__(self, monsoon_config, lvpm_monsoon_bin=None,
                 hvpm_monsoon_bin=None):
        """Constructs _BitsServiceMonsoonConfig.

        Args:
            monsoon_config: The monsoon config as defined in the
            ACTS Bits controller config. Expected format is:
              { 'serial_num': <serial number:int>,
                'monsoon_voltage': <voltage:double> }
            lvpm_monsoon_bin: Binary file to interact with low voltage monsoons.
            Needed if the monsoon is a lvpm monsoon (serial number lower than
            20000).
            hvpm_monsoon_bin: Binary file to interact with high voltage
            monsoons. Needed if the monsoon is a hvpm monsoon (serial number
            greater than 20000).
        """
        if 'serial_num' not in monsoon_config:
            raise ValueError(
                'Monsoon serial_num can not be undefined. Received '
                'config was: %s' % monsoon_config)
        if 'monsoon_voltage' not in monsoon_config:
            raise ValueError('Monsoon voltage can not be undefined. Received '
                             'config was: %s' % monsoon_config)

        self.serial_num = monsoon_config['serial_num']
        self.monsoon_voltage = monsoon_config['monsoon_voltage']

        self.config_dic = copy.deepcopy(DEFAULT_MONSOON_CONFIG_DICT)
        if float(self.serial_num) >= 20000:
            self.config_dic['hv_monsoon'] = 1
            if hvpm_monsoon_bin is None:
                raise ValueError('hvpm_monsoon binary is needed but was None. '
                                 'Received config was: %s' % monsoon_config)
            self.monsoon_binary = hvpm_monsoon_bin
        else:
            self.config_dic['hv_monsoon'] = 0
            if lvpm_monsoon_bin is None:
                raise ValueError('lvpm_monsoon binary is needed but was None. '
                                 'Received config was: %s' % monsoon_config)
            self.monsoon_binary = lvpm_monsoon_bin

        self.config_dic['monsoon_binary_path'] = self.monsoon_binary
        self.config_dic['monsoon_voltage'] = self.monsoon_voltage
        self.config_dic['serial_num'] = self.serial_num


DEFAULT_SERVICE_CONFIG_DICT = {
    'devices': {
        'default_device': {
            'enabled': 1,
            'collectors': {}
        }
    }
}


class BitsServiceConfig(object):
    """Helper object to construct a bits_service config from a bits controller
    config and required additional resources, such as paths to executables.

    The format for bits_service's configuration is explained in:
    go/pixel-bits/user-guide/service/configuration.md

    Attributes:
        config_dic: A bits_service configuration as a python dictionary.
    """

    def __init__(self, controller_config, lvpm_monsoon_bin=None,
                 hvpm_monsoon_bin=None):
        """Creates a BitsServiceConfig.

        Args:
            controller_config: The config as defined in the ACTS  BiTS
            controller config. Expected format is:
              {
                (optional) 'Monsoon': { 'serial_num': <serial number:int>,
                                        'monsoon_voltage': <voltage:double> }
              }
            lvpm_monsoon_bin: Binary file to interact with low voltage monsoons.
            Needed if the monsoon is a lvpm monsoon (serial number lower than
            20000).
            hvpm_monsoon_bin: Binary file to interact with high voltage
            monsoons. Needed if the monsoon is a hvpm monsoon (serial number
            greater than 20000).
        """
        self.config_dic = copy.deepcopy(DEFAULT_SERVICE_CONFIG_DICT)
        self.has_monsoon = False
        self.monsoon_config = None
        if 'Monsoon' in controller_config:
            self.has_monsoon = True
            self.monsoon_config = _BitsMonsoonConfig(
                controller_config['Monsoon'],
                lvpm_monsoon_bin,
                hvpm_monsoon_bin)
            self.config_dic['devices']['default_device']['collectors'][
                'Monsoon'] = self.monsoon_config.config_dic
        self.has_kibble = False
