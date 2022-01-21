"""Make sure the user build configuration is working as expected.

Although we can assume the features should be the same between user and user_debug build,
the configuration difference between this two build are not tested.

In this test suite, we modify the gps configuration to be the same as user build
and check if the setting is working.
"""
import os
import shutil
import tempfile
import time

from acts import asserts
from acts import signals
from acts.base_test import BaseTestClass
from acts.test_decorators import test_tracker_info
from acts_contrib.test_utils.gnss import gnss_test_utils as gutils


class GnssUserBuildBroadcomConfigurationTest(BaseTestClass):
    """ GNSS user build configuration Tests on Broadcom device."""
    def setup_class(self):
        super().setup_class()
        self.ad = self.android_devices[0]

        if not gutils.check_chipset_vendor_by_qualcomm(self.ad):
            gutils._init_device(self.ad)
            self.gps_config_path = tempfile.mkdtemp()
            self.gps_config_path_on_dut = "/vendor/etc/gnss"
            self.gps_config_names = ["gps.xml", "scd.conf", "lhd.conf"]
            self.set_gps_logenabled(enable=True)
            self.backup_gps_config()

    def teardown_class(self):
        if hasattr(self, "gps_config_path") and os.path.isdir(self.gps_config_path):
            shutil.rmtree(self.gps_config_path)

    def setup_test(self):
        if gutils.check_chipset_vendor_by_qualcomm(self.ad):
            raise signals.TestSkip("Device is Qualcomm, skip the test")
        gutils.clear_logd_gnss_qxdm_log(self.ad)

    def teardown_test(self):
        if not gutils.check_chipset_vendor_by_qualcomm(self.ad):
            self.revert_gps_config()

    def on_fail(self, test_name, begin_time):
        self.ad.take_bug_report(test_name, begin_time)
        gutils.get_gnss_qxdm_log(self.ad)

    def backup_gps_config(self):
        """Copy the gps config

        config file will be copied: gps.xml / lhd.conf / scd.conf
        """
        for name in self.gps_config_names:
            file_path = os.path.join(self.gps_config_path_on_dut, name)
            self.ad.log.debug("Backup %s", file_path)
            self.ad.adb.pull(file_path, self.gps_config_path)

    def revert_gps_config(self):
        """Revert the gps config from the one we backup in the setup_class

        config file will be reverted: gps.xml / lhd.conf / scd.conf
        """
        self.ad.adb.remount()
        for name in self.gps_config_names:
            file_path = os.path.join(self.gps_config_path, name)
            self.ad.log.debug("Revert %s to %s", name, self.gps_config_path_on_dut)
            self.ad.adb.push(file_path, self.gps_config_path_on_dut)

    def change_file_content_by_sed(self, pattern, target, file_path):
        """Modify file via sed command

        command will be sed -i 's/<pattern>/<target>/g' <file_path>
        Args:
            pattern: source string used to search in file
            target: string that will overwrite the matched result
            file_path: full path to the file
        """
        self.ad.adb.remount()
        command = f"sed -i 's/{pattern}/{target}/g' {file_path}"
        self.ad.log.debug("sed command: %s", command)
        self.ad.adb.shell(command)

    def run_gps_and_capture_log(self):
        """Enable GPS via gps tool for 15s and capture pixel log"""
        gutils.start_pixel_logger(self.ad)
        gutils.start_gnss_by_gtw_gpstool(self.ad, state=True)
        time.sleep(15)
        gutils.start_gnss_by_gtw_gpstool(self.ad, state=False)
        gutils.stop_pixel_logger(self.ad)

    def set_gps_logenabled(self, enable):
        """Set LogEnabled in gps.xml / lhd.conf / scd.conf

        Args:
            enable: True to enable / False to disable
        """
        key = "LogEnabled"
        value_src = "false" if enable else "true"
        value_dest = "true" if enable else "false"

        for name in self.gps_config_names:
            path = os.path.join(self.gps_config_path_on_dut, name)
            # in gps.xml, the true / false should be wrapped in ""
            # for lhd and scd conf, no need to wrap "" around the true / false
            pattern = f"{key}=\"{value_src}\"" if name == "gps.xml" else f"{key}={value_src}"
            target = f"{key}=\"{value_dest}\"" if name == "gps.xml" else f"{key}={value_dest}"
            self.change_file_content_by_sed(pattern, target, path)
            result = self.ad.adb.shell(f"grep {key} {path}")
            self.ad.log.debug("%s setting %s", name, result)

    @test_tracker_info(uuid="1dd68d9c-38b0-4fbc-8635-1228c72872ff")
    def test_gps_logenabled_setting(self):
        """Veifry the LogEnabled setting in gps.xml / scd.conf / lhd.conf
        Steps:
            1. default setting is on in user_debug build
            2. enable gps for 15s
            3. assert gps log pattern "slog    :" in pixel logger
            4. disable LogEnabled in all the gps conf
            5. enable gps for 15s
            6. assert gps log pattern "slog    :" in pixel logger
        """
        self.run_gps_and_capture_log()
        result, _ = gutils.parse_brcm_nmea_log(self.ad, "slog    :", [])
        asserts.assert_true(bool(result), "LogEnabled is set to true, but no gps log was found")

        self.set_gps_logenabled(enable=False)
        gutils.clear_logd_gnss_qxdm_log(self.ad)

        self.run_gps_and_capture_log()
        result, _ = gutils.parse_brcm_nmea_log(self.ad, "slog    :", [])
        asserts.assert_false(bool(result),("LogEnabled is set to False but still found %d slog",
                                           len(result)))
