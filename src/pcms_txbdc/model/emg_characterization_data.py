from dataclasses import dataclass, field, fields
from datetime import datetime
from typing import BinaryIO
from platformdirs import user_data_dir
import struct
import os
import numpy as np

from .fileio_helpers import FileIO_Helpers
from .application_configuration import ApplicationConfiguration

@dataclass
class EmgHistogramData:
    min: float = 0.0
    max: float = 0.0
    mean: float = 0.0
    std_dev: float = 0.0
    n: float = 0.0
    quartiles: list[float] = field(default_factory=list)
    step_size_one_percent: float = 0.0
    histogram_values: np.ndarray = field(default_factory=lambda: np.zeros(1))
    histogram_bin_edges: np.ndarray = field(default_factory=lambda: np.zeros(1))

@dataclass
class EmgCharacterizationHeader:
    file_version: int = 0
    subject_id: str = ""
    session_datetime: datetime = datetime.min
    stage_name: str = ""
    stage_description: str = ""
    stage_type: int = 0

    bin_duration_ms: int = 0
    trial_initiation_uv_min: float = 0
    trial_initiation_uv_max: float = 0
    trial_initiation_phase_min_ms: int = 0
    trial_initiation_phase_max_ms: int = 0

    def read_from_file (self, fid: BinaryIO) -> None:
        self.file_version = FileIO_Helpers.read(fid, "int32")
        self.subject_id = FileIO_Helpers.read_string(fid)
        self.session_datetime = FileIO_Helpers.read_datetime(fid)
        self.stage_name = FileIO_Helpers.read_string(fid)
        self.stage_description = FileIO_Helpers.read_string(fid)
        self.stage_type = FileIO_Helpers.read(fid, "int32")

        self.trial_initiation_uv_min = FileIO_Helpers.read(fid, "float64")
        self.trial_initiation_uv_max = FileIO_Helpers.read(fid, "float64")
        self.trial_initiation_phase_min_ms = FileIO_Helpers.read(fid, "int32")
        self.trial_initiation_phase_max_ms = FileIO_Helpers.read(fid, "int32")
        self.bin_duration_ms = FileIO_Helpers.read(fid, "int32")

        pass

@dataclass
class EmgCharacterizationTrial:

    trial_datetime: datetime = datetime.min
    grand_mean: float = 0.0
    bins: list[float] = field(default_factory=list)
    monitored_signal: list[float] = field(default_factory=list)

    def read_from_file (self, fid: BinaryIO) -> None:
        self.trial_datetime = FileIO_Helpers.read_datetime(fid)
        self.grand_mean = FileIO_Helpers.read(fid, "float64")

        self.bins.clear()
        N: int = FileIO_Helpers.read(fid, "int32")
        for i in range(0, N):
            self.bins.append(FileIO_Helpers.read(fid, "float64"))
        
        self.monitored_signal.clear()
        N = FileIO_Helpers.read(fid, "int32")
        for i in range(0, N):
            self.monitored_signal.append(FileIO_Helpers.read(fid, "float64"))


@dataclass
class EmgCharacterizationData:

    header: EmgCharacterizationHeader = None
    trials: list[EmgCharacterizationTrial] = field(default_factory=list)

    def read (self, fid: BinaryIO) -> None:
        '''
        Readers the EMG characterization data file from disk.
        '''

        self.header = EmgCharacterizationHeader()
        self.header.read_from_file(fid)

        while (True):
            chunk: bytes = fid.read(4)
            if (not chunk):
                break

            block_id: int = struct.unpack(FileIO_Helpers.type_dictionary["int32"], chunk)[0]
            if (block_id == 1):
                trial: EmgCharacterizationTrial = EmgCharacterizationTrial()
                trial.read_from_file(fid)

                self.trials.append(trial)
        
        pass

    def get_all_grandmeans (self) -> list[float]:
        '''
        Generates a list that contains the grandmean from each trial and
        returns the list to the caller.
        '''

        result: list[float] = [t.grand_mean for t in self.trials]
        return result
    
    def get_histogram_data (self) -> EmgHistogramData:
        '''
        Calculates histogram data that is used by other pieces of the application.
        '''

        #Instantiate an object to hold the histogram data
        histogram_data: EmgHistogramData = EmgHistogramData()

        #Get the list of grand means
        grand_means: list[float] = self.get_all_grandmeans()

        #Calculate the min, max, mean, std dev, and quartiles
        histogram_data.min = min(grand_means)
        histogram_data.max = max(grand_means)
        histogram_data.n = len(grand_means)
        histogram_data.std_dev = np.std(grand_means)

        histogram_data.quartiles.clear()
        histogram_data.quartiles.append(np.quantile(grand_means, 0.25))
        histogram_data.quartiles.append(np.quantile(grand_means, 0.50))
        histogram_data.quartiles.append(np.quantile(grand_means, 0.75))

        histogram_data.step_size_one_percent = np.quantile(grand_means, 0.01) - histogram_data.min

        (histogram_data.histogram_values, histogram_data.histogram_bin_edges) = np.histogram(grand_means)

        #Return the histogram data to the caller
        return histogram_data

    #region Static methods

    @staticmethod
    def find_all_emg_characterization_data_files (subject_id: str) -> list[str]:
        #Generate the path for this subject id
        app_data_path: str = user_data_dir(ApplicationConfiguration.appname, ApplicationConfiguration.appauthor)
        subject_file_path: str = f"{app_data_path}/{subject_id}/"

        #Find all files with the expected file extension
        files_list: list[str] = os.listdir(subject_file_path)

        #Create an array to hold the result
        result: list[str] = []

        #Find the first file with the "hrs1" file extension
        for f in files_list:
            if (f.endswith("hrs1")):
                result.append(f)

        return result

    #endregion
