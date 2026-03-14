import numpy as np
import pandas as pd
from pydas.constants import CP_WATER
from scipy.linalg import expm


class RCBuilding:
    def __init__(self, parameters):
        self.state = None
        self.parameters = parameters
        self.indoor_temperature = 20.0 # Degrees Celsius.
        self.temperature_setpoint_day = 21.0 # Degrees Celsius
        self.temperature_setpoint_night = 18.0 # Degrees Celsius

    def update_rcbuilding_temperature(self, timestep: float, current_external_heating: float, current_outdoor_temperature: float) -> None:
        raise NotImplementedError("You are required to implement the time stepping update for an RCBuilding.")

    def setpoint_temperature_callback(self, time_of_day) -> float:
        is_day = (8 <= time_of_day <= 22)
        return self.temperature_setpoint_day if is_day else self.temperature_setpoint_night


class RCBuilding1R1C(RCBuilding):
    def __init__(self, parameters):
        super().__init__(parameters)
        self.state = {"indoor_temperature": self.indoor_temperature}

    def update_rcbuilding_temperature(self, timestep: float, current_external_heating: float, current_outdoor_temperature: float) -> None:
        euler_step = timestep / self.parameters["thermal_capacitance"]
        delta_T = self.indoor_temperature - current_outdoor_temperature
        self.indoor_temperature += euler_step * (current_external_heating - self.parameters["thermal_conductance"] * delta_T)
    

class RCBuilding2R2C(RCBuilding):
    def __init__(self, parameters):
        super().__init__(parameters)
        self.wall_temperature = 20.0 # Degree Celsius.
        self.state = {"indoor_temperature": self.indoor_temperature, "wall_temperature": self.wall_temperature}
        G_a, G_w = self.parameters["thermal_conductance_air"], self.parameters["thermal_conductance_wall"]
        k_a, k_w = self.parameters["thermal_capacitance_air"], self.parameters["thermal_capacitance_wall"]
        self.system_matrix = np.array([
            [-G_a / k_a, G_a / k_a],
            [G_a / k_w, -(G_a + G_w) / k_w]
        ])
        self.system_matrix_inv = np.linalg.inv(self.system_matrix)
        self.input_matrix = np.array([
            [1.0 / k_a, 0.0],
            [0.0, G_w / k_w]
        ])
    
    def update_rcbuilding_temperature(self, timestep: float, current_external_heating: float, current_outdoor_temperature: float) -> None:
        current_state = np.array([self.state["indoor_temperature"], self.state["wall_temperature"]])
        current_input = np.array([current_external_heating, current_outdoor_temperature])
        system_step_matrix = expm(self.system_matrix * timestep)
        input_step_matrix = self.system_matrix_inv @ (system_step_matrix - np.identity(2)) @ self.input_matrix
        new_state = system_step_matrix @ current_state + input_step_matrix @ current_input
        self.state["indoor_temperature"] = new_state[0]
        self.state["wall_temperature"] = new_state[1]


class RCBuilding3R2C(RCBuilding):
    def __init__(self, parameters):
        super().__init__(parameters)
        self.wall_temperature = 20.0 # Degree Celsius.
        self.state = {"indoor_temperature": self.indoor_temperature, "wall_temperature": self.wall_temperature}
        G_a, G_w = self.parameters["thermal_conductance_air"], self.parameters["thermal_conductance_wall"]
        k_a, k_w = self.parameters["thermal_capacitance_air"], self.parameters["thermal_capacitance_wall"]
        mass_flow = self.parameters["mass_flow"]
        self.system_matrix = np.array([
            [-(G_a + mass_flow * CP_WATER) / k_a, G_a / k_a],
            [G_a / k_w, -(G_a + G_w) / k_w]
        ])
        self.system_matrix_inv = np.linalg.inv(self.system_matrix)
        self.input_matrix = np.array([
            [0.0, mass_flow * CP_WATER / k_a],
            [G_w / k_w, 0.0]
        ])
    
    def update_rcbuilding_temperature(self, timestep: float, current_supply_temperature: float, current_outdoor_temperature: float) -> None:
        current_state = np.array([self.state["indoor_temperature"], self.state["wall_temperature"]])
        current_input = np.array([current_outdoor_temperature, current_supply_temperature])
        system_step_matrix = expm(self.system_matrix * timestep)
        input_step_matrix = self.system_matrix_inv @ (system_step_matrix - np.identity(2)) @ self.input_matrix
        new_state = system_step_matrix @ current_state + input_step_matrix @ current_input
        self.state["indoor_temperature"] = new_state[0]
        self.state["wall_temperature"] = new_state[1]


class SupplyController:
    def __init__(self, maximum_heating_power):
        self.maximum_heating_power = maximum_heating_power
        self.supply_temperature_upper = 90.0 # Degree Celsius.
        self.supply_temperature_lower = 75.0 # Degree Celsius.

    def setpoint_schedule(self, rcbuilding: RCBuilding, time_of_day: float) -> float:
        is_below_setpoint = (rcbuilding.state["indoor_temperature"] <= rcbuilding.setpoint_temperature_callback(time_of_day = time_of_day))
        return self.maximum_heating_power if is_below_setpoint else 0.0
    
    def static_setpoint_schedule(self, rcbuilding: RCBuilding, static_setpoint: float) -> float:
        is_below_setpoint = (rcbuilding.indoor_temperature <= static_setpoint)
        return self.maximum_heating_power if is_below_setpoint else 0.0
    
    def supply_temperature_schedule(self, rcbuilding: RCBuilding, time_of_day: float) -> float:
        is_below_setpoint = (rcbuilding.state["indoor_temperature"] <= rcbuilding.setpoint_temperature_callback(time_of_day = time_of_day))
        return self.supply_temperature_upper if is_below_setpoint else self.supply_temperature_lower


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
    
    def get_outdoor_temperature(self) -> float:
        return self.outdoor_temperature_data["Lufttemperatur"][self.current_time_step]

    def get_current_hour_of_day(self):
        return self.outdoor_temperature_data["timestamp"].dt.hour[self.current_time_step]
    
    def get_extracted_heat(self) -> float:
        current_indoor_temperature = self.rcbuilding.state["indoor_temperature"]
        current_supply_temperature = self.controller.supply_temperature_schedule(rcbuilding = self.rcbuilding, time_of_day = self.get_current_hour_of_day())
        return self.rcbuilding.parameters["mass_flow"] * CP_WATER * (current_supply_temperature - current_indoor_temperature)

    def step(self) -> None: # TODO: Implement multiple building using an array with for-looping! 
        current_heating_power = self.controller.setpoint_schedule(rcbuilding = self.rcbuilding, time_of_day = self.get_current_hour_of_day())
        self.rcbuilding.update_rcbuilding_temperature(timestep = self.timestep, current_external_heating = current_heating_power, current_outdoor_temperature = self.get_outdoor_temperature())
        self.current_time_step += 1

    def step_ST(self) -> None: # TODO: Implement multiple building using an array with for-looping! 
        current_supply_temperature = self.controller.supply_temperature_schedule(rcbuilding = self.rcbuilding, time_of_day = self.get_current_hour_of_day())
        self.rcbuilding.update_rcbuilding_temperature(timestep = self.timestep, current_supply_temperature = current_supply_temperature, current_outdoor_temperature = self.get_outdoor_temperature())
        self.current_time_step += 1