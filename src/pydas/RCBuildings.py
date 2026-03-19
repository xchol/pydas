import numpy as np
import pandas as pd
from pydas.constants import CP_WATER
from scipy.linalg import expm


class RCBuilding:
    def __init__(self, thermal_resistances, thermal_capacitances, timestep):
        self.state = None
        self.thermal_resistances = thermal_resistances
        self.thermal_capacitances = thermal_capacitances
        self.timestep = timestep
        self.current_timestep = 0
        self.indoor_temperature = 20.0 # Degrees Celsius.
        self.setpoint_default = 21.0 # Default setpoint temperature of indoor air in degrees Celsius.
        self.setpoint_day = 21.0 # Degrees Celsius
        self.setpoint_night = 18.0 # Degrees Celsius
        self.daytimes = np.array([8, 22]) # By default, daytime (in hours of the day) is between 8 AM and 22 PM.

    def step(self, current_external_heating: float, current_outdoor_temperature: float) -> None:
        raise NotImplementedError("You are required to implement the time stepping update for an RCBuilding.")
    
    def set_day_night_setpoints(self, setpoint_day: float, setpoint_night: float, daytime_from: int, daytime_to: int) -> None:
        self.setpoint_day = setpoint_day
        self.setpoint_night = setpoint_night
        self.daytimes = [daytime_from, daytime_to]

    def get_day_night_setpoint(self, time_of_day) -> float:
        is_day = (self.daytimes.min() <= time_of_day <= self.daytimes.max())
        return self.setpoint_day if is_day else self.setpoint_night


class RCBuilding1R1C(RCBuilding):
    def __init__(self, thermal_resistances, thermal_capacitances, timestep):
        super().__init__(thermal_resistances, thermal_capacitances, timestep)
        self.state = {"indoor_temperature": self.indoor_temperature}

    def step(self, current_external_heating: float, current_outdoor_temperature: float) -> None:
        euler_step = self.timestep / self.thermal_capacitances["C1"]
        delta_T = self.state["indoor_temperature"] - current_outdoor_temperature
        self.state["indoor_temperature"] += euler_step * (current_external_heating - delta_T / self.thermal_resistances["R1"])
        self.current_timestep += 1
    

class RCBuilding2R2C(RCBuilding):
    def __init__(self, thermal_resistances, thermal_capacitances, timestep):
        super().__init__(thermal_resistances, thermal_capacitances, timestep)
        self.state = {"indoor_temperature": self.indoor_temperature, "T2": 20.0} # Initial conditions for the two states of the model.
        self.R1C1_inv = 1.0 / (self.thermal_resistances["R1"] * self.thermal_capacitances["C1"]) 
        self.R1C2_inv = 1.0 / (self.thermal_resistances["R1"] * self.thermal_capacitances["C2"])
        self.R2C2_inv = 1.0 / (self.thermal_resistances["R2"] * self.thermal_capacitances["C2"])
        self.system_matrix = np.array([[-self.R1C1_inv, self.R1C1_inv], [self.R1C2_inv, -(self.R1C2_inv + self.R2C2_inv)]])
        self.system_matrix_inv = np.linalg.inv(self.system_matrix)
        self.input_matrix = np.array([[0.0, 1.0 / self.thermal_capacitances["C1"]],[self.R2C2_inv, 0.0]])
    
    def step(self, current_external_heating: float, current_outdoor_temperature: float) -> None:
        current_state = np.array([self.state["indoor_temperature"], self.state["T2"]])
        current_input = np.array([current_outdoor_temperature, current_external_heating])
        system_step_matrix = expm(self.system_matrix * self.timestep)
        input_step_matrix = self.system_matrix_inv @ (system_step_matrix - np.identity(2)) @ self.input_matrix
        new_state = system_step_matrix @ current_state + input_step_matrix @ current_input
        self.state["indoor_temperature"], self.state["T2"] = new_state
        self.current_timestep += 1


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