import numpy as np
import pandas as pd


class RCBuilding:
    def __init__(self, thermal_conductance, thermal_capacitance, RC_type):
        self.thermal_conductance = thermal_conductance
        self.thermal_capacitance = thermal_capacitance
        self.RC_type = RC_type # The type of RC-network model to be used in the thermal simulation.
        self.indoor_temperature = 20.0 # Degrees Celsius.
        self.temperature_setpoint_day = 21.0 # Degrees Celsius
        self.temperature_setpoint_night = 18.0 # Degrees Celsius
    
    def _1R1C_callback(self, timestep: float, external_heating: float, current_outdoor_temperature: float) -> None:
        current_indoor_temperature = self.indoor_temperature
        self.indoor_temperature += (timestep / self.thermal_capacitance) * \
        (external_heating - self.thermal_conductance * (current_indoor_temperature - current_outdoor_temperature))

    def setpoint_temperature_callback(self, time_of_day) -> float:
        is_day = (8 <= time_of_day <= 22)
        return self.temperature_setpoint_day if is_day else self.temperature_setpoint_night

    def update_building_temperature(self, timestep: float, external_heating: float, current_outdoor_temperature: float) -> None:
        if self.RC_type == "1R1C": self._1R1C_callback(timestep, external_heating, current_outdoor_temperature)
        elif self.RC_type == "2R2C": pass
        else: assert False, "Please specify a RC-network type."


class SupplyController:
    def __init__(self, maximum_heating_power):
        self.maximum_heating_power = maximum_heating_power

    def setpoint_schedule(self, rcbuilding: RCBuilding, time_of_day: float) -> float:
        is_below_setpoint = (rcbuilding.indoor_temperature <= rcbuilding.setpoint_temperature_callback(time_of_day = time_of_day))
        return self.maximum_heating_power if is_below_setpoint else 0.0


class BuildingEnergySimulator:
    def __init__(self, timestep: float):
        self.rcbuilding = None
        self.controller = None
        self.outdoor_temperature_data = None
        self.timestep = timestep
        self.current_time_step = 0
    
    def add_controller(self, controller: SupplyController) -> None:
        self.controller = controller

    def add_rcbuilding(self, rcbuilding: RCBuilding) -> None:
        self.rcbuilding = rcbuilding
    
    def load_outdoor_temperature_data(self, path_to_file: string) -> None:
        with open(path_to_file, encoding = "utf-8") as file:
            for index, line in enumerate(file):
                if line.startswith("Datum"):
                    header_row = index
                    break

        dataframe = pd.read_csv(path_to_file, sep=";", skiprows = header_row)
        dataframe["timestamp"] = pd.to_datetime(dataframe["Datum"] + " " + dataframe["Tid (UTC)"])
        self.outdoor_temperature_data = dataframe

    def step(self) -> None:
        current_outdoor_temperature = self.outdoor_temperature_data["Lufttemperatur"][self.current_time_step]
        time_of_day = self.outdoor_temperature_data["timestamp"].dt.hour[self.current_time_step]
        current_heating_power = self.controller.setpoint_schedule(rcbuilding = self.rcbuilding, time_of_day = time_of_day)
        self.rcbuilding.update_building_temperature(self.timestep, current_heating_power, current_outdoor_temperature)
        self.current_time_step += 1