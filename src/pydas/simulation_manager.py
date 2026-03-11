import numpy as np
import pandas as pd


class SimpleBuilding:
    def __init__(self, thermal_conductance, thermal_capacitance):
        self.thermal_conductance = thermal_conductance
        self.thermal_capacitance = thermal_capacitance
        self.indoor_temperature = 20.0 # Degrees Celsius.
        self.temperature_setpoint = 20.0 # Degrees Celsius


class BuildingEnergySimulator:
    def __init__(self, timestep: float):
        self.building = None
        self.outdoor_temperature_data = None
        self.timestep = timestep
        
    def add_building(self, building: SimpleBuilding):
        self.building = building
    
    def load_outdoor_temperature_data(self, path_to_file: string):
        with open(path_to_file, encoding = "utf-8") as file:
            for index, line in enumerate(file):
                if line.startswith("Datum"):
                    header_row = index
                    break

        dataframe = pd.read_csv(path_to_file, sep=";", skiprows = header_row)
        dataframe["timestamp"] = pd.to_datetime(dataframe["Datum"] + " " + dataframe["Tid (UTC)"])
        self.outdoor_temperature_data = dataframe

    
    def advance(self, number_of_time_steps: int = 0):
        for iteration in range(number_of_time_steps):
            previous_temperature = self.building.indoor_temperature
            self.building.indoor_temperature += (self.timestep / building.thermal_capacitance) * \
                  (Q_dhn - self.building.thermal_conductance * (previous_temperature - outdoor_temperature))
    