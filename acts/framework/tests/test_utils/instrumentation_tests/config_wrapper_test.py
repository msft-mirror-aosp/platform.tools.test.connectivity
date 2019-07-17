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

from acts.test_utils.instrumentation_tests.config_wrapper import ConfigWrapper
from acts.test_utils.instrumentation_tests.config_wrapper import InvalidParamError


REAL_PATHS = ['realpath/1', 'realpath/2']
MOCK_CONFIG = {
    'big_int': 50000,
    'small_int': 5,
    'float': 7.77,
    'real_paths_only': REAL_PATHS,
    'real_and_fake_paths': [
        'realpath/1', 'fakepath/0'
    ],
}


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

    def test_get_int(self):
        """Test that get_int() returns the value if it is an int, and raises
        an exception if it isn't.
        """
        self.assertEqual(self.mock_config.get_int('small_int'),
                         MOCK_CONFIG['small_int'])
        with self.assertRaisesRegex(InvalidParamError, 'of type int'):
            self.mock_config.get_int('float')

    def test_get_float(self):
        """Test that get_float() returns the value if it is a float, and raises
        an exception if it isn't.
        """
        self.assertEqual(self.mock_config.get_float('float'),
                         MOCK_CONFIG['float'])
        with self.assertRaisesRegex(InvalidParamError, 'of type float'):
            self.mock_config.get_float('small_int')

    @mock.patch('os.path.exists', side_effect=lambda f: f in REAL_PATHS)
    def test_get_files(self, *_):
        """Test that get_files() returns the list of files only if all of the
        paths actually exist.
        """
        self.assertEqual(self.mock_config.get_files('real_paths_only'),
                         MOCK_CONFIG['real_paths_only'])
        with self.assertRaisesRegex(InvalidParamError, 'Cannot resolve'):
            self.mock_config.get_files('real_and_fake_paths')


if __name__ == '__main__':
    unittest.main()
