import pandas as pd

class ClimateData:
    def __init__(self):
        pass

    @staticmethod
    def load_csv_from_smhi(path_to_file: string) -> pd.DataFrame:
        with open(path_to_file, encoding = "utf-8") as file:
            for index, line in enumerate(file):
                if line.startswith("Datum"):
                    header_row = index
                    break

        dataframe = pd.read_csv(path_to_file, sep = ";", skiprows = header_row)
        dataframe["timestamp"] = pd.to_datetime(dataframe["Datum"] + " " + dataframe["Tid (UTC)"])
        return dataframe
    

    

    