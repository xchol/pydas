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
