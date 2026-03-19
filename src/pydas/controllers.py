class PIDController:
    def __init__(self, maximal_heating_power, K_p, K_i = 0.0, K_d = 0.0):
        self.error = 0.0
        self.accumulative_error = 0.0
        self.maximal_heating_power = maximal_heating_power
        self.heating_power = maximal_heating_power
        self.K_p = K_p
        self.K_i = K_i
        self.K_d = K_d

    def correct(self, timestep: float, indoor_temperature: float, setpoint_temperature: float) -> None:
        observed_error = (setpoint_temperature - indoor_temperature) # Temperature difference is the error here. 
        self.error = observed_error
        self.accumulative_error += observed_error * timestep
        new_heating_power = self.K_p * observed_error + self.K_i * self.accumulative_error
        new_heating_power_clamped = max(0.0, min(new_heating_power, self.maximal_heating_power))
        if new_heating_power != new_heating_power_clamped:
            self.accumulative_error -= observed_error * timestep # Revert in order to avoid infinitely growing integral term.
        self.heating_power = new_heating_power_clamped # Heating power cannot be negative nor exceed the maximal heating power output.