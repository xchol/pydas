import numpy as np
import pandas as pd


class SimpleBuilding:
    def __init__(self, thermal_conductance, thermal_capacitance):
        self.thermal_conductance = thermal_conductance
        self.thermal_capacitance = thermal_capacitance
        self.indoor_temperature = 20.0 # Degrees Celsius.
        self.temperature_setpoint_day = 21.0 # Degrees Celsius
        self.temperature_setpoint_night = 18.0 # Degrees Celsius

    def setpoint_temperature_callback(self, time_of_day) -> float:
        is_day = (8 <= time_of_day <= 22)
        return self.temperature_setpoint_day if is_day else self.temperature_setpoint_night


class SupplyController:
    def __init__(self, maximum_heating_power):
        self.maximum_heating_power = maximum_heating_power

    def setpoint_schedule(self, indoor_temperature: float, setpoint_temperature: float) -> float:
        is_below_setpoint = (indoor_temperature <= setpoint_temperature)
        return self.maximum_heating_power if is_below_setpoint else 0.0


class BuildingEnergySimulator:
    def __init__(self, timestep: float):
        self.building = None
        self.controller = None
        self.outdoor_temperature_data = None
        self.timestep = timestep
        self.current_time_step = 0
    
    def add_controller(self, controller: SupplyController) -> None:
        self.controller = controller

    def add_building(self, building: SimpleBuilding) -> None:
        self.building = building
    
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
        current_indoor_temperature = self.building.indoor_temperature
        current_outdoor_temperature = self.outdoor_temperature_data["Lufttemperatur"][self.current_time_step]
        time_of_day = self.outdoor_temperature_data["timestamp"].dt.hour[self.current_time_step]
        current_temperature_setpoint = self.building.setpoint_temperature_callback(time_of_day)
        current_heating_power = self.controller.setpoint_schedule(indoor_temperature = current_indoor_temperature, setpoint_temperature = current_temperature_setpoint)
        self.building.indoor_temperature += (self.timestep / self.building.thermal_capacitance) * \
              (current_heating_power - self.building.thermal_conductance * (current_indoor_temperature - current_outdoor_temperature))
        self.current_time_step += 1