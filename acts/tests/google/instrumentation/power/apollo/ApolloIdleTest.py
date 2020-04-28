from acts.test_utils.instrumentation.power import instrumentation_power_test


class ApolloIdleTest(instrumentation_power_test.InstrumentationPowerTest):
    """Test class for running instrumentation test idle system cases. Tests in
    this class should be executed assuming there is no SL4A installed."""

    def _prepare_device(self):
        super()._prepare_device()
        self.base_device_configuration()

    def __init__(self, configs):
        super().__init__(configs)
        # clear additional command options that won't work on the average
        # OEM devices.
        self._instrumentation_command_options = {}

    def run_idle_test_case(self):
        self.run_and_measure(
            'com.google.android.device.power.tests.RockBottom',
            'rockBottom')
        self.validate_power_results()

    def test_apollo_rock_bottom(self):
        """Measures power when the device is in a rock bottom state."""
        self.run_idle_test_case()