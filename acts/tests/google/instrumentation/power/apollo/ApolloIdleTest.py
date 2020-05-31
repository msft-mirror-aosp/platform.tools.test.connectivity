from acts.test_utils.instrumentation.power.apollo.ApolloBaseTest import ApolloBaseTest


class ApolloIdleTest(ApolloBaseTest):
    """Test class for running instrumentation test Apollo system idle cases"""

    def test_apollo_rock_bottom(self):
        """Measures power when the device is in a rock bottom state. This
        test is made to use the newer power-tests.apk."""
        self.run_and_measure(
            'com.google.android.device.power.tests.RockBottom',
            'rockBottom')
        self.validate_power_results()

    def test_apollo_idle_system_screen_off(self):
        """Measures power when the device is in a rock bottom state. This
        test is made to use the older Power.apk."""
        self.run_and_measure(
            'com.google.android.platform.powertests.IdleTestCase',
            'testIdleScreenOff')
        self.validate_power_results()

    def test_apollo_scanning_off(self):
        """Measures power when the device is not scanning, but the apollo feature is installed"""

        # TODO: change the below command to using _stop_scanning once b/156301031 is resolved
        # Not disabling the consent dialog is a workaround.
        self._disable_consent_dialog = False
        self._sideload_apollo()

        self.run_and_measure(
            'com.google.android.platform.powertests.IdleTestCase',
            'testIdleScreenOff')
        self.validate_power_results()

    def test_apollo_scanning(self):
        """Measures power when the device is scanning"""

        # If specific scanning frequencies and times were passed in, used those
        # Otherwise, just use the default API behavior
        self._scan_interval_seconds = self._instrumentation_config.get('scan_interval_seconds')
        self._scan_time_seconds = self._instrumentation_config.get('scan_time_seconds')

        self._sideload_apollo()
        self._start_scanning()

        self.run_and_measure(
            'com.google.android.platform.powertests.IdleTestCase',
            'testIdleScreenOff')
        self.validate_power_results()
