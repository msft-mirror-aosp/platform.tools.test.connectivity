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
from mock import MagicMock

from acts import context
from acts.test_utils.instrumentation.config_wrapper import ConfigWrapper
from acts.test_utils.instrumentation.config_wrapper import ContextualConfigWrapper
from acts.test_utils.instrumentation.config_wrapper import InvalidParamError
from acts.test_utils.instrumentation.config_wrapper import merge

REAL_PATHS = ['realpath/1', 'realpath/2']
MOCK_CONFIG = {
    'big_int': 50000,
    'small_int': 5,
    'float': 7.77,
    'string': 'insert text here',
    'real_paths_only': REAL_PATHS,
    'real_and_fake_paths': [
        'realpath/1', 'fakepath/0'
    ],
    'inner_config': {
        'inner_val': 16
    }
}

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


class ContextualConfigWrapperTest(unittest.TestCase):
    @mock.patch('acts.context.get_current_context')
    def test_get_controller_config_for_test_case(self, mock_get_current_context):
        """Test that _get_controller_config returns the corresponding
        controller config for the current test case.
        """
        mock_case_context = mock.MagicMock(spec=context.TestCaseContext)
        mock_case_context.test_class_name = 'MockInstrumentationBaseTest'
        mock_case_context.test_case_name = 'test_case'
        mock_get_current_context.return_value = mock_case_context

        config = ContextualConfigWrapper(
            MOCK_INSTRUMENTATION_CONFIG).get_config('MockController')

        self.assertEqual(config.get('param1'), 1)
        self.assertEqual(config.get('param2'), 2)
        self.assertEqual(config.get('param3'), 3)

    @mock.patch('acts.context.get_current_context')
    def test_get_controller_config_for_test_class(self, mock_current_context):
        """Test that _get_controller_config returns the controller config for
        the current test class (while no test case is running).
        """
        mock_class_context = MagicMock(spec=context.TestClassContext)
        mock_class_context.test_class_name = 'MockInstrumentationBaseTest'
        mock_current_context.return_value = mock_class_context

        config = ContextualConfigWrapper(
            MOCK_INSTRUMENTATION_CONFIG).get_config('MockController')

        self.assertEqual(config.get('param1'), 1)
        self.assertEqual(config.get('param2'), 2)
        self.assertEqual(config.get('param3'), 5)

    @mock.patch('acts.context.get_current_context')
    def test_original_config_is_accessible(self, mock_get_current_context):
        """Test that _get_controller_config returns the corresponding
        controller config for the current test case.
        """
        mock_case_context = mock.MagicMock(spec=context.TestCaseContext)
        mock_case_context.test_class_name = 'MockInstrumentationBaseTest'
        mock_case_context.test_case_name = 'test_case'
        mock_get_current_context.return_value = mock_case_context

        config = ContextualConfigWrapper(
            MOCK_INSTRUMENTATION_CONFIG)

        self.assertEqual(config.original_config, MOCK_INSTRUMENTATION_CONFIG)


class ConfigWrapperTest(unittest.TestCase):
    """Unit tests for the Config Wrapper."""

    def setUp(self):
        self.mock_config = ConfigWrapper(MOCK_CONFIG)

    def test_get_returns_correct_value(self):
        """Test that get() returns the correct param value."""
        self.assertEqual(self.mock_config.get('big_int'),
                         MOCK_CONFIG['big_int'])

    def test_get_missing_param_returns_default(self):
        """Test that get() returns the default value if no param with the
        requested name is found.
        """
        default_val = 17
        self.assertEqual(self.mock_config.get('missing', default=default_val),
                         default_val)

    def test_get_with_custom_verification_method(self):
        """Test that get() verifies the param with the user-provided test
        function.
        """
        verifier = lambda i: i > 100
        msg = 'Value too small'
        self.assertEqual(self.mock_config.get('big_int', verify_fn=verifier,
                                              failure_msg=msg),
                         MOCK_CONFIG['big_int'])
        with self.assertRaisesRegex(InvalidParamError, msg):
            self.mock_config.get('small_int', verify_fn=verifier,
                                 failure_msg=msg)

    def test_get_config(self):
        """Test that get_config() returns an empty ConfigWrapper if no
        sub-config exists with the given name.
        """
        ret = self.mock_config.get_config('missing')
        self.assertIsInstance(ret, ConfigWrapper)
        self.assertFalse(ret)

    def test_get_int(self):
        """Test that get_int() returns the value if it is an int, and raises
        an exception if it isn't.
        """
        self.assertEqual(self.mock_config.get_int('small_int'),
                         MOCK_CONFIG['small_int'])
        with self.assertRaisesRegex(InvalidParamError, 'of type int'):
            self.mock_config.get_int('float')

    def test_get_numeric(self):
        """Test that get_numeric() returns the value if it is an int or float,
        and raises an exception if it isn't.
        """
        self.assertEqual(self.mock_config.get_numeric('small_int'),
                         MOCK_CONFIG['small_int'])
        self.assertEqual(self.mock_config.get_numeric('float'),
                         MOCK_CONFIG['float'])
        with self.assertRaisesRegex(InvalidParamError, 'of type int or float'):
            self.mock_config.get_numeric('string')

    def test_config_wrapper_wraps_recursively(self):
        """Test that dict values within the input config get transformed into
        ConfigWrapper objects themselves.
        """
        self.assertTrue(
            isinstance(self.mock_config.get('inner_config'), ConfigWrapper))
        self.assertEqual(
            self.mock_config.get('inner_config').get_int('inner_val'), 16)

    def test_merge_appending_values(self):
        """Test that the merge function appends non-conflicting values.
        """
        a = ConfigWrapper({'a': 1})
        b = ConfigWrapper({'b': 2})
        result = merge(a, b)
        self.assertEqual(result, ConfigWrapper({'a': 1, 'b': 2}))

    def test_update_conflicting_values(self):
        """Test that the merge function appends non-conflicting values.
        """
        a = ConfigWrapper({'a': 1})
        b = ConfigWrapper({'a': [1, 2, 3]})
        result = merge(a, b)
        self.assertEqual(result, ConfigWrapper({'a': [1, 2, 3]}))

    def test_merge_merges_sub_dictionaries_recursively(self):
        """Test that the merge function merges internal dictionaries
        recursively.
        """
        a = ConfigWrapper({'dic': {'a': 0, 'c': 3, 'sub': {'x': 1}}})
        b = ConfigWrapper({'dic': {'a': 2, 'b': 2, 'sub': {'y': 2}}})
        result = merge(a, b)
        self.assertEqual(result,
                         ConfigWrapper({'dic': {'a': 2, 'b': 2, 'c': 3,
                                                'sub': {'x': 1, 'y': 2}}}))


if __name__ == '__main__':
    unittest.main()
