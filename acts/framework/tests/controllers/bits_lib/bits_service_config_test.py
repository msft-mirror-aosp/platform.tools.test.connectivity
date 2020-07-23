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

import unittest
import mock

from acts.controllers.bits_lib import bits_service_config


class BitsServiceConfigTest(unittest.TestCase):

    def test_monsoon_with_serial_less_than_20000_is_configured_as_non_hv(self):
        config = bits_service_config._BitsMonsoonConfig(
            {'serial_num': 19999, 'monsoon_voltage': 1},
            lvpm_monsoon_bin='lvpm_bin', hvpm_monsoon_bin='hvpm_bin')
        self.assertEqual(0, config.config_dic['hv_monsoon'])
        self.assertEqual('lvpm_bin', config.config_dic['monsoon_binary_path'])

    def test_lvpm_monsoon_requires_lvpm_binary(self):
        self.assertRaisesRegex(ValueError,
                               r'lvpm_monsoon binary is needed but was None.',
                               bits_service_config._BitsMonsoonConfig,
                               {'serial_num': 19999, 'monsoon_voltage': 1},
                               hvpm_monsoon_bin='hvpm_bin')

    def test_monsoon_with_serial_greater_than_20000_is_configured_as_hv(self):
        config = bits_service_config._BitsMonsoonConfig(
            {'serial_num': 20001, 'monsoon_voltage': 1},
            lvpm_monsoon_bin='lvpm_bin', hvpm_monsoon_bin='hvpm_bin')
        self.assertEqual(1, config.config_dic['hv_monsoon'])
        self.assertEqual('hvpm_bin', config.config_dic['monsoon_binary_path'])

    def test_hvpm_monsoon_requires_hvpm_binary(self):
        self.assertRaisesRegex(ValueError,
                               r'hvpm_monsoon binary is needed but was None.',
                               bits_service_config._BitsMonsoonConfig,
                               {'serial_num': 20001, 'monsoon_voltage': 1},
                               lvpm_monsoon_bin='hvpm_bin')

    def test_monsoon_config_fails_without_voltage(self):
        self.assertRaisesRegex(ValueError,
                               r'Monsoon voltage can not be undefined.',
                               bits_service_config._BitsMonsoonConfig,
                               {'serial_num': 1},
                               lvpm_monsoon_bin='lvpm_bin')

    def test_monsoon_config_fails_without_serial(self):
        self.assertRaisesRegex(ValueError,
                               r'Monsoon serial_num can not be undefined.',
                               bits_service_config._BitsMonsoonConfig,
                               {'monsoon_voltage': 1},
                               lvpm_monsoon_bin='lvpm_bin')

    def test_monsoon_config_is_always_enabled(self):
        config = bits_service_config._BitsMonsoonConfig(
            {'serial_num': 1, 'monsoon_voltage': 1},
            lvpm_monsoon_bin='bin')
        self.assertEqual(1, config.config_dic['enabled'])

    def test_monsoon_config_disables_monsoon_reseting(self):
        config = bits_service_config._BitsMonsoonConfig(
            {'serial_num': 1, 'monsoon_voltage': 1},
            lvpm_monsoon_bin='bin')
        self.assertEqual(0, config.config_dic['monsoon_reset'])

    def test_monsoon_config_type_is_monsooncollector(self):
        config = bits_service_config._BitsMonsoonConfig(
            {'serial_num': 1, 'monsoon_voltage': 1},
            lvpm_monsoon_bin='bin')
        self.assertEqual('monsooncollector', config.config_dic['type'])

    def test_bits_service_config_has_an_enabled_default_device(self):
        service_config = bits_service_config.BitsServiceConfig({})
        self.assertIn('devices', service_config.config_dic)
        self.assertIn('default_device', service_config.config_dic['devices'])
        self.assertEqual(1,
                         service_config.config_dic['devices']['default_device'][
                             'enabled'])

    def test_bits_service_config_without_monsoon(self):
        service_config = bits_service_config.BitsServiceConfig({})
        self.assertFalse(service_config.has_monsoon)

    def test_bits_service_config_without_kibble(self):
        service_config = bits_service_config.BitsServiceConfig({})
        self.assertFalse(service_config.has_kibble)

    def test_bits_service_config_with_a_monsoon(self):
        service_config = bits_service_config.BitsServiceConfig(
            {'Monsoon': {'serial_num': 1, 'monsoon_voltage': 1}},
            lvpm_monsoon_bin='bin')
        config_dic = service_config.config_dic

        self.assertTrue(service_config.has_monsoon)
        self.assertIn('devices', config_dic)
        self.assertIn('default_device', config_dic['devices'])
        self.assertIn('collectors',
                      config_dic['devices']['default_device'])
        self.assertIn('Monsoon',
                      config_dic['devices']['default_device'][
                          'collectors'])

        monsoon_config = bits_service_config._BitsMonsoonConfig(
            {'serial_num': 1, 'monsoon_voltage': 1},
            lvpm_monsoon_bin='bin').config_dic
        self.assertEqual(monsoon_config,
                         config_dic['devices']['default_device'][
                             'collectors']['Monsoon'])


if __name__ == '__main__':
    unittest.main()
