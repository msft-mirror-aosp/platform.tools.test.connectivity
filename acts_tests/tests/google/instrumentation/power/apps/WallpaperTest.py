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


from acts.test_utils.instrumentation.power import instrumentation_power_test

SMALL_FILE_PUSH_TIMEOUT = 10

class WallpaperTest(instrumentation_power_test.InstrumentationPowerTest):
  """Test class for running instrumentation test static wallpaper cases."""

  def _prepare_device(self):
    super()._prepare_device()
    self.base_device_configuration()

  def run_static_wallpaper_test_case(self):
    wallpaper_location = self.push_to_external_storage(
        self.get_file_from_config('wallpaper_location'),
        timeout=SMALL_FILE_PUSH_TIMEOUT)
    self.trigger_scan_on_external_storage()

    metrics = self.run_and_measure(
        'com.google.android.platform.powertests.WallpaperTests',
        'testStaticWallpaper',
        extra_params=[('wallpaper_location', wallpaper_location)])
    self.record_metrics(metrics)
    self.validate_metrics(metrics)

  def test_photo_wallpaper(self):
    """Measures power when the device is screen on with a wallpaper."""
    self.run_static_wallpaper_test_case()