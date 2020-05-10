from acts.test_utils.instrumentation.power import instrumentation_power_test


class ApolloIdleTest(instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running instrumentation test idle system cases. Tests in
    this class should be executed assuming there is no SL4A installed."""

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()

    def setup_test(self):
        super().setup_test()
        # clear command options that won't work on OEM devices.
        self._instr_cmd_builder.set_output_as_text()
        self._instr_cmd_builder.remove_flag('--no-isolated-storage')

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