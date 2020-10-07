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

import mock

import unittest
from unittest.mock import MagicMock

from acts.test_utils.instrumentation.config_wrapper import ConfigWrapper


from acts.test_utils.instrumentation.device.command.adb_command_types import \
    GenericCommand
from acts.test_utils.instrumentation.instrumentation_base_test import \
    InstrumentationBaseTest

MOCK_INSTRUMENTATION_CONFIG = {
    'MockController': {
        'param1': 1,
        'param2': 4
    },
    'MockInstrumentationBaseTest': {
        'MockController': {
            'param2': 2,
            'param3': 5
        },
        'test_case': {
            'MockController': {
                'param3': 3
            }
        }
    }
}


class MockInstrumentationBaseTest(InstrumentationBaseTest):
    """Mock test class to initialize required attributes."""

    def __init__(self):
        self.current_test_name = None
        self.ad_dut = mock.Mock()
        self.log = mock.Mock()
        self._instrumentation_config = ConfigWrapper(MOCK_INSTRUMENTATION_CONFIG)
        self._class_config = self._instrumentation_config.get_config(
            self.__class__.__name__)


class InstrumentationBaseTestTest(unittest.TestCase):
    def setUp(self):
        self.instrumentation_test = MockInstrumentationBaseTest()

    def test_adb_run_literal_commands(self):
        result = self.instrumentation_test.adb_run('ls /something')
        self.assertIn('ls /something', result.keys())

        result = self.instrumentation_test.adb_run(
            ['ls /something', 'ls /other'])
        self.assertIn('ls /something', result.keys())
        self.assertIn('ls /other', result.keys())

    def test_adb_run_generic_commands(self):
        result = self.instrumentation_test.adb_run(
            GenericCommand('ls /something'))
        self.assertIn('ls /something', result.keys())

        result = self.instrumentation_test.adb_run(
            [GenericCommand('ls /something'),
             GenericCommand('ls /other')])
        self.assertIn('ls /something', result.keys())
        self.assertIn('ls /other', result.keys())

    def test_bugreport_on_fail_by_default(self):
        self.instrumentation_test._instrumentation_config = ConfigWrapper({})
        self.instrumentation_test._take_bug_report = MagicMock()

        self.instrumentation_test.on_exception('test', 0)
        self.assertEqual(1,
                         self.instrumentation_test._take_bug_report.call_count)
        self.instrumentation_test.on_pass('test', 0)
        self.assertEqual(2,
                         self.instrumentation_test._take_bug_report.call_count)
        self.instrumentation_test.on_fail('test', 0)
        self.assertEqual(3,
                         self.instrumentation_test._take_bug_report.call_count)

    def test_bugreport_on_end_events_can_be_disabled(self):
        self.instrumentation_test._instrumentation_config = ConfigWrapper({
                'bugreport_on_pass': False,
                'bugreport_on_exception': False,
                'bugreport_on_fail': False
            })
        self.instrumentation_test._take_bug_report = MagicMock()

        self.instrumentation_test.on_exception('test', 0)
        self.instrumentation_test.on_pass('test', 0)
        self.instrumentation_test.on_fail('test', 0)
        self.assertFalse(self.instrumentation_test._take_bug_report.called)


if __name__ == '__main__':
    unittest.main()
