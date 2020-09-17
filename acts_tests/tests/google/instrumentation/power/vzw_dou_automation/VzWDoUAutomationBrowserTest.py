#!/usr/bin/env python3
#
#   Copyright 2020 - The Android Open Source Project
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

from acts.test_decorators import repeated_test
from acts.test_utils.instrumentation.power.vzw_dou_automation import \
  vzw_dou_automation_base_test
from acts.test_utils.instrumentation.device.command.adb_commands import common


class VzWDoUAutomationBrowserTest(
    vzw_dou_automation_base_test.VzWDoUAutomationBaseTest):
  """Class for running VZW DoU browsing test cases"""

  @repeated_test(
      num_passes=3,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_browser(self, attempt_number):
    """Measures power when the device is browsing."""

    metrics = self.run_and_measure(
        'com.google.android.platform.dou.BrowserTests',
        'testBrowser',
        attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  @repeated_test(
      num_passes=3,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_streaming_video(self, attempt_number):
    """Measures power when the device is streaming video."""

    metrics = self.run_and_measure(
        'com.google.android.platform.dou.YouTubeV15Tests',
        'testStreamingVideo',
        attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  @repeated_test(
      num_passes=3,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_video_recording(self, attempt_number):
    """Measures power when the device is recording."""

    metrics = self.run_and_measure(
        'com.google.android.platform.dou.CameraVideoRecordingTests',
        'testVideoRecording',
        attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  @repeated_test(
      num_passes=3,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_video_playback(self, attempt_number):
    """Measures power when the device is playing video."""

    self.log_in_gmail_account()
    self.push_movies_to_dut()
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.PhotosVideoPlaybackTests',
        'testVideoPlayback',
        attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  @repeated_test(
      num_passes=3,
      acceptable_failures=2,
      result_selector=vzw_dou_automation_base_test.get_median_current)
  def test_audio_playback(self, attempt_number):
    """Measures power when the device is playing audio."""

    self.log_in_gmail_account()
    self.push_music_to_dut()
    metrics = self.run_and_measure(
        'com.google.android.platform.dou.YTMusicPlaybackTests',
        'testAudioPlayback',
        attempt_number=attempt_number)
    self.record_metrics(metrics)
    self.validate_metrics(metrics)
