from acts.test_utils.instrumentation.device.apps.app_installer import AppInstaller
from acts.test_utils.instrumentation.power import instrumentation_power_test

import time


class ApolloBaseTest(instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running instrumentation test idle system cases.

    Many functions shamelessly copied from:
        google3/wireless/android/apollo/test/lib/apollo_decorator.py
    """

    def __init__(self, configs):
        super().__init__(configs)
        self.supported_hooks = {'start', 'stop'}
        self._apk_install_wait_time_seconds = 5
        self._scan_interval_seconds = None
        self._scan_time_seconds = None
        # TODO: remove once b/156301031 is resolved
        self._disable_consent_dialog = True

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()

    def setup_test(self):
        super().setup_test()
        # clear command options that won't work on OEM devices.
        self._instr_cmd_builder.set_output_as_text()
        self._instr_cmd_builder.remove_flag('--no-isolated-storage')

    def _set_nearby_phenotype_flag(self, flag_name, flag_type, flag_value):
        self.adb_run(f'am broadcast -a "com.google.android.gms.phenotype.FLAG_OVERRIDE" --es package "com.google.android.gms.nearby" ' \
                     f'--es user "*" --esa flags "{flag_name}" --esa values "{flag_value}" --esa types "{flag_type}" com.google.android.gms')

    def _set_installation_overrides(self):
        self._set_nearby_phenotype_flag('exposure_notification_enable_client_apps_whitelist', 'boolean', 'false')
        if self._disable_consent_dialog:
            self._set_nearby_phenotype_flag('exposure_notification_use_consent_dialog_for_all_clients', 'boolean', 'false')

        # Scanning interval and scanning time need to be set here, before scanning starts
        if self._scan_interval_seconds:
            self._set_nearby_phenotype_flag('contact_tracing_scan_interval_second', 'long', str(self._scan_interval_seconds))
        if self._scan_time_seconds:
            self._set_nearby_phenotype_flag('contact_tracing_scan_time_second', 'long', str(self._scan_time_seconds))

    def _start_scanning(self):
        self._issue_apollo_test_hook_command('start')

    def _issue_apollo_test_hook_command(self, hook_command, payload=None, time_to_wait_seconds=10):
        if hook_command not in self.supported_hooks:
            raise ValueError(f'Unsupported apollo test hook {hook_command}')
        # Send a hook command, which is handled by the apollo test APK
        self.adb_run(f'am start-foreground-service -a {hook_command} com.google.android.apps.exposurenotification/.debug.HookService')
        # Wait for success and timeout on a failure. The test app does not explicitly tell you if the call failed.
        start_time = time.time()
        while time.time() - start_time < time_to_wait_seconds:
            if self.ad_dut.search_logcat(f'HookService: Success:{hook_command}'):
                return True
            time.sleep(1)
        raise RuntimeError(f'HookService:{hook_command} did not finish in {time_to_wait_seconds} seconds')

    def _sideload_apollo(self):
        self.ad_dut.adb.ensure_root()

        self.adb_run('logcat -c')  # Clear previous logcat information - reflashing is not performed for Apollo

        # Uninstall old APK's and clear flags
        gmscore_apk_file = self.get_file_from_config('gmscore_file_' + self.ad_dut.serial)
        gmscore_apk = AppInstaller(self.ad_dut, gmscore_apk_file)
        gmscore_apk.uninstall()
        nearby_module_apk_file = self.get_file_from_config('gmscore_nearby_en_file_' + self.ad_dut.serial)
        nearby_module_apk = AppInstaller(self.ad_dut, nearby_module_apk_file)
        nearby_module_apk.uninstall()
        apollo_test_apk_file = self.get_file_from_config('exposure_notification_app')
        apollo_test_apk = AppInstaller(self.ad_dut, apollo_test_apk_file)
        apollo_test_apk.uninstall()

        # Set up BT and location
        self.adb_run('service call bluetooth_manager 6')
        self.adb_run('settings put secure location_providers_allowed +gps')
        self.adb_run('settings put secure location_mode 3')

        # Install gmscore
        gmscore_apk.install()
        # Give gmscore some time to initialize (there doesn't appear to be a logcat message to key off)
        time.sleep(self._apk_install_wait_time_seconds)

        # Whitelist EN for sideloading
        self.adb_run('am broadcast -a com.google.gservices.intent.action.GSERVICES_OVERRIDE -e gms:chimera:dev_module_packages "com.google.android.gms.policy_nearby"')
        # Install EN module
        nearby_module_apk.install()
        # Give EN some time to initialize (there doesn't appear to be a logcat message to key off)
        time.sleep(self._apk_install_wait_time_seconds)

        # Whitelist test app and disable consent dialogs
        self._set_installation_overrides()

        # Install test apk
        apollo_test_apk.install()
        # Give the test app some time to initialize (there doesn't appear to be a logcat message to key off)
        time.sleep(self._apk_install_wait_time_seconds)