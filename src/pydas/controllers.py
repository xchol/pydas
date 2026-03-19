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

class SupplyController:
    def __init__(self, maximum_heating_power):
        self.maximum_heating_power = maximum_heating_power
        self.supply_temperature_upper = 90.0 # Degree Celsius.
        self.supply_temperature_lower = 75.0 # Degree Celsius.
    
    def setpoint_schedule(self, rcbuilding: RCBuilding, time_of_day: float) -> float:
        is_below_setpoint = (rcbuilding.state["indoor_temperature"] <= rcbuilding.get_day_night_setpoint(time_of_day = time_of_day))
        return self.maximum_heating_power if is_below_setpoint else 0.0
    
    def static_setpoint_schedule(self, rcbuilding: RCBuilding, static_setpoint: float) -> float:
        is_below_setpoint = (rcbuilding.indoor_temperature <= static_setpoint)
        return self.maximum_heating_power if is_below_setpoint else 0.0
    
    def supply_temperature_schedule(self, rcbuilding: RCBuilding, time_of_day: float) -> float:
        is_below_setpoint = (rcbuilding.state["indoor_temperature"] <= rcbuilding.setpoint_temperature_callback(time_of_day = time_of_day))
        return self.supply_temperature_upper if is_below_setpoint else self.supply_temperature_lower
