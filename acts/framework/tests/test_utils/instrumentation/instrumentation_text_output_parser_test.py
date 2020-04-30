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

import os
import unittest

from acts.test_utils.instrumentation import instrumentation_text_output_parser

SAMPLE_WITH_LONG_STATUSES = 'data/instrumentation_text_output_parser/long_statuses.txt'
SAMPLE_WITH_LONG_INSTRUMENTATION_RESULT = 'data/instrumentation_text_output_parser/long_instrumentation_result.txt'
SAMPLE_WITH_20_AS_SESSION_RESULT_CODE = 'data/instrumentation_text_output_parser/session_result_code_is_20.txt'
SAMPLE_WITH_42_AS_TEST_STATUS_RESULT_CODE = 'data/instrumentation_text_output_parser/test_status_result_code_is_42.txt'


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

    def test_multiline_status_gets_parsed_correctly(self):
        file = os.path.join(os.path.dirname(__file__),
                            SAMPLE_WITH_LONG_STATUSES)

        session = instrumentation_text_output_parser.parse_from_file(
            file)

        long_message_entry = session.test_status[0].results.entries[0]
        self.assertEqual(long_message_entry.key, 'long_message')
        self.assertEqual(long_message_entry.value_string.split('\n'),
                         ['lorem', 'ipsum', 'dolor'])
        longer_message_entry = session.test_status[1].results.entries[0]
        self.assertEqual(longer_message_entry.key, 'longer_message')
        self.assertEqual(longer_message_entry.value_string.split('\n'),
                         ['lorem', 'ipsum', 'dolor', 'sit', 'amet'])

    def test_multiline_instrumentation_result_gets_parsed_correctly(self):
        file = os.path.join(os.path.dirname(__file__),
                            SAMPLE_WITH_LONG_INSTRUMENTATION_RESULT)

        session = instrumentation_text_output_parser.parse_from_file(
            file)

        entry = session.session_status.results.entries[0]
        self.assertEqual(entry.key, 'long_result')
        self.assertEqual(entry.value_string.split('\n'),
                         ['never', 'gonna', 'give', 'you', 'up', 'never',
                          'gonna', 'let', 'you', 'down'])

    def test_session_result_code(self):
        file = os.path.join(os.path.dirname(__file__),
                            SAMPLE_WITH_20_AS_SESSION_RESULT_CODE)

        session = instrumentation_text_output_parser.parse_from_file(
            file)

        self.assertEqual(session.session_status.result_code, 20)


    def test_test_status_result_code(self):
        file = os.path.join(os.path.dirname(__file__),
                            SAMPLE_WITH_42_AS_TEST_STATUS_RESULT_CODE)

        session = instrumentation_text_output_parser.parse_from_file(
            file)

        self.assertEqual(session.test_status[0].result_code, 42)


if __name__ == '__main__':
    unittest.main()
