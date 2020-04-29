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

from acts.test_utils.instrumentation import instrumentation_text_output_parser


class InstrumentationTextOutputParserTest(unittest.TestCase):

    def test_get_test_result_code(self):
        code = instrumentation_text_output_parser._extract_status_code(
            'INSTRUMENTATION_STATUS_CODE: 9',
            instrumentation_text_output_parser._Markers.STATUS_CODE)

        self.assertEqual(code, 9)

    def test_get_session_result_code(self):
        code = instrumentation_text_output_parser._extract_status_code(
            'INSTRUMENTATION_CODE: 7',
            instrumentation_text_output_parser._Markers.CODE)

        self.assertEqual(code, 7)

    def test_get_test_status_key_value(self):
        (key, value) = instrumentation_text_output_parser._extract_key_value(
            'INSTRUMENTATION_STATUS: hello=world',
            instrumentation_text_output_parser._Markers.STATUS)

        self.assertEqual(key, 'hello')
        self.assertEqual(value, 'world')

    def test_get_session_result_key_value(self):
        (key, value) = instrumentation_text_output_parser._extract_key_value(
            'INSTRUMENTATION_RESULT: hola=mundo',
            instrumentation_text_output_parser._Markers.STATUS)

        self.assertEqual(key, 'hola')
        self.assertEqual(value, 'mundo')


if __name__ == '__main__':
    unittest.main()
