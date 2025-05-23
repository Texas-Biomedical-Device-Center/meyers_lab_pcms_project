import numpy as np
from random import Random
from datetime import datetime
import pyqtgraph as pg
from typing import BinaryIO
from platformdirs import user_data_dir
import os

from PySide6 import QtCore

from .stage import Stage
from ..session_message import SessionMessage
from ..application_configuration import ApplicationConfiguration
from ..fileio_helpers import FileIO_Helpers

from ..stimjim import StimJim

class SalineBathDemoDataStage (Stage):

    #region Constants

    #This defines the time between activation of two stimjims
    STIM_GAP_MILLISECONDS: float = 0.2

    #This defines the wait time after a stimulation in milliseconds
    STIM_WAIT_MILLISECONDS: int = 100

    #This defines the number of stimulation to be done
    STIM_INSTANCE_DURATION_SAMPLE_COUNT: int = 10

    #endregion

    #region Constructor

    def __init__(self):
        super().__init__()

        #Set the basic stage information
        self.stage_name = "S0"
        self.stage_description = "Saline Bath Demo Data"
        self.stage_type = Stage.STAGE_TYPE_SALINE_DEMO_DATA

        #Create a private variable that will be used to store a save-file handle
        self._fid: BinaryIO = None

        #Make sure that the stimulation parameters are set on the StimJims
        ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters_on_stimjim(0, Stage.STIM1_AMPLITUDE)
        ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters_on_stimjim(1, Stage.STIM2_AMPLITUDE)
       
    #endregion

    #region Overrides

    def initialize (self, subject_id: str) -> tuple[bool, str]:
        #Set the subject id
        self._subject_id: str = subject_id

        #Set the stimulation count to 0
        self._stimulation_count = 0

        #Get the current datetime
        current_datetime: datetime = datetime.now()

        #Define the path where we will save data
        app_data_path: str = user_data_dir(ApplicationConfiguration.appname, ApplicationConfiguration.appauthor)
        file_path: str = os.path.join(app_data_path, self._subject_id)

        #Define a file name for the file to which we will save data
        file_timestamp: str = current_datetime.strftime("%Y%m%dT%H%M%S")
        file_name: str = f"{self._subject_id}_{file_timestamp}.hrs1"

        #Create the folder if it does not yet exist
        if (not os.path.exists(file_path)):
            os.makedirs(file_path)
        
        #If we reach this point in the code, then no pre-existing hrs1 file exists for this subject, so we may proceed.

        #Open a file for saving data
        self._fid = open(os.path.join(file_path, file_name), "wb")

        #Save the file header for this data file
        self._save_file_header()

        #Return from this function
        return (True, "")

    def process (self, data: np.ndarray) -> None:
        '''
        Processes the most recent incoming data and takes any actions
        that are necessary based on the incoming data.
        '''

        #Now let's proceed
        if (self._is_trial_set_up):
            #Add the number of samples we are pulling in to the current trial sample count
            self._current_trial_sample_count += len(data)

            #Pull in new data to the monitored signal - and take the absolute value of the data
            self._monitored_signal = np.concatenate([self._monitored_signal, np.abs(data)])
            elements_to_remove: int = len(self._monitored_signal) - self._monitored_signal_sample_count
            if (elements_to_remove > 0):
                self._monitored_signal = self._monitored_signal[elements_to_remove:]

            #Bin the data
            for bin_index in range(0, len(self._bins)):
                bin_start = SalineBathDemoDataStage.BIN_DURATION_SAMPLE_COUNT * bin_index
                bin_end = SalineBathDemoDataStage.BIN_DURATION_SAMPLE_COUNT * (bin_index + 1)

                if (bin_end > len(self._monitored_signal)):
                    bin_end = len(self._monitored_signal)

                bin_mean: float = np.mean(self._monitored_signal[bin_start:bin_end])
                self._bins[bin_index] = bin_mean
            
            #Get the mean of all the bins
            bin_grand_mean: float = np.mean(self._bins)

            #If the bin grand mean is within a pre-specified min or max range, then
            #we consider this a trial initiation.
            if ((self._current_trial_sample_count >= self._monitored_signal_sample_count) and
                (bin_grand_mean >= SalineBathDemoDataStage.TRIAL_INITIATION_MIN_RANGE_MICROVOLTS) and 
                (bin_grand_mean <= SalineBathDemoDataStage.TRIAL_INITIATION_MAX_RANGE_MICROVOLTS)):

                #A trial has been initiatied...

                #Add the grand mean to the list of trial means
                self._trial_means.append(bin_grand_mean)

                #Save the trial to the data file
                self._save_trial(bin_grand_mean)

                #Let's create a message object
                message: SessionMessage = SessionMessage(f"Trial {len(self._trial_means)} initiated")
                self.signals.new_message.emit(message)

                #Reset the trial-is-set-up flag
                self._is_trial_set_up = False

                #Reset the current trial sample count
                self._current_trial_sample_count = 0

                pass

        return

    def finalize (self) -> None:        
        if (self._fid is not None):
            #Close the data file for this session
            self._fid.close()

    # def get_trial_plot_options (self) -> list[str]:
    #     return ["Most recent trial"]
    
    # def get_session_plot_options (self) -> list[str]:
    #     return ["Session history"]

    # def update_trial_plot (self) -> None:
    #     #This stage will not support updating the plots from an external call.
    #     pass

    # def update_session_plot (self) -> None:
    #     #This stage will not support updating the plots from an external call.
    #     pass

    # #endregion

    #region Private methods

    def _setup_new_trial (self) -> None:
        #Choose a trial-initiation monitoring duration
        dur_milliseconds: int = self._rng.randint(
            SalineBathDemoDataStage.TRIAL_INITIATION_PHASE_MIN_DURATION_MILLISECONDS,
            SalineBathDemoDataStage.TRIAL_INITIATION_PHASE_MAX_DURATION_MILLISECONDS
        )

        #Round the number to the nearest 50-ms
        dur_milliseconds = self._round_special(dur_milliseconds, 50)

        #Convert to seconds
        self._monitored_signal_duration_seconds = float(dur_milliseconds) / 1000.0

        #Set the number of samples that we care about
        self._monitored_signal_sample_count = int(self._monitored_signal_duration_seconds * Stage.SAMPLE_RATE)

        #Get the number of bins we will be collecting
        bin_count: int = int(dur_milliseconds / SalineBathDemoDataStage.BIN_DURATION_MILLISECONDS)

        #Re-size the appropriate arrays to hold the data we care about
        self._monitored_signal = np.zeros(self._monitored_signal_sample_count)
        self._bins = np.zeros(bin_count)

        #Set the flag indicating that the trial has been set up
        self._is_trial_set_up = True

        #We are done. return from this function.
        return

    def _round_special (self, x: int, base: int = 50) -> int:
        return base * int(round(float(x) / float(base)))

    def _save_file_header (self) -> None:
        if (self._fid is not None):
            #Save the file version
            FileIO_Helpers.write(self._fid, "int32", int(0))

            #Save the subject id
            FileIO_Helpers.write_string(self._fid, self._subject_id)

            #Save the session date/time
            FileIO_Helpers.write_datetime(self._fid, datetime.now())

            #Save the stage name
            FileIO_Helpers.write_string(self._fid, self.stage_name)

            #Save the stage description
            FileIO_Helpers.write_string(self._fid, self.stage_description)

            #Save the stage type
            FileIO_Helpers.write(self._fid, "int32", self.stage_type)

            #Save the min and max range for trial initiation
            FileIO_Helpers.write(self._fid, "float64", SalineBathDemoDataStage.TRIAL_INITIATION_MIN_RANGE_MICROVOLTS)
            FileIO_Helpers.write(self._fid, "float64", SalineBathDemoDataStage.TRIAL_INITIATION_MAX_RANGE_MICROVOLTS)

            #Save the min and max recording duration for trial initiation criteria
            FileIO_Helpers.write(self._fid, "int32", SalineBathDemoDataStage.TRIAL_INITIATION_PHASE_MIN_DURATION_MILLISECONDS)
            FileIO_Helpers.write(self._fid, "int32", SalineBathDemoDataStage.TRIAL_INITIATION_PHASE_MAX_DURATION_MILLISECONDS)

            #Save the bin width
            FileIO_Helpers.write(self._fid, "int32", SalineBathDemoDataStage.BIN_DURATION_MILLISECONDS)

            pass

    def _save_trial (self, bin_grand_mean: float) -> None:
        if (self._fid is not None):

            #Save a trial block header
            FileIO_Helpers.write(self._fid, "int32", int(1))

            #Save a datetime for the trial initiation
            FileIO_Helpers.write_datetime(self._fid, datetime.now())

            #Save the bin grand mean
            FileIO_Helpers.write(self._fid, "float64", bin_grand_mean)

            #Save the number of bins
            FileIO_Helpers.write(self._fid, "int32", len(self._bins))

            #Save all of the bin data
            for i in range(0, len(self._bins)):
                FileIO_Helpers.write(self._fid, "float64", self._bins[i])
            
            #Save the length of the monitored signal
            FileIO_Helpers.write(self._fid, "int32", len(self._monitored_signal))

            #Save all of the monitored signal data
            for i in range(0, len(self._monitored_signal)):
                FileIO_Helpers.write(self._fid, "float64", self._monitored_signal[i])
            
            pass

    #endregion