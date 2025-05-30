import numpy as np
from datetime import datetime
import time
import os
from typing import BinaryIO
from platformdirs import user_data_dir
from PySide6 import QtCore

from .stage import Stage
from ..session_message import SessionMessage
from ..application_configuration import ApplicationConfiguration
from ..fileio_helpers import FileIO_Helpers

from ..stimjim import StimJim

class SalineBathDemoDataStage(Stage):
    #region Constants

    # This defines the gap (ms) between StimJim1 and StimJim2 activation
    STIM_GAP_MILLISECONDS: float = 100.0
    
    # This defines the wait time (sec) after stimulations were induced
    STIM_INTERVAL_SECONDS: float = 5.0

    # This defines the number of stimulations to induce. For demodata collection, any small number would work.
    STIM_INSTANCE_COUNT: int = 5

    #endregion

    #region Methods

    def save (self, fid: BinaryIO) -> None:
        #Save a trial block indicator
        FileIO_Helpers.write(fid, "int32", int(1))

        #Save the timestamp for this trial
        FileIO_Helpers.write_datetime(fid, self._stim_phase_timestamp)

        #Save the trial data
        for i in range(0, len(self.demo_data)):
            FileIO_Helpers.write(fid, "float64", self.demo_data[i])

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

        #Create a numpy array to hold the demo data
        self.demo_data: np.ndarray = np.zeros(1)
        
        # Create a variable to track how many stims were made
        self._stim_index: int = 0
        
        # Set the phase of the stage
        self._stim_phase: str = "STIM1"
        self._stim_phase_timestamp: float = None

        # Set up StimJim parameters
        ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters_on_stimjim(0, Stage.STIM1_AMPLITUDE)
        ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters_on_stimjim(1, Stage.STIM2_AMPLITUDE)

    #endregion

    #region Overrides

    def initialize(self, subject_id: str) -> tuple[bool, str]:
        # Set the subject id
        self._subject_id = subject_id

        #Create a numpy array to hold the demo data
        self.demo_data: np.ndarray = np.zeros(1)

        # Create a variable to track how many stims were made
        self._stim_index = 0

        # Set the phase of the stage
        self._stim_phase = "STIM1"

        # Create a time stamp for when the stimulation was activated
        self._stim_phase_timestamp = None

        #Get the current datetime
        current_datetime: datetime = datetime.now()

        #Define the path where we will save data
        app_data_path: str = user_data_dir(ApplicationConfiguration.appname, ApplicationConfiguration.appauthor)
        file_path: str = os.path.join(app_data_path, self._subject_id)

        #Create the folder if it does not yet exist
        if (not os.path.exists(file_path)):
            os.makedirs(file_path)

        #Define a file name for the file to which we will save data
        file_timestamp: str = current_datetime.strftime("%Y%m%dT%H%M%S")
        file_name: str = f"{self._subject_id}_{file_timestamp}.hrs1"

        #Open a file for saving data for this stage
        self._fid = open(os.path.join(file_path, file_name), "wb")

        #Save the file header for this data file
        self._save_file_header()

        #Return from this function
        return (True, "")

    def process(self, data: np.ndarray) -> None:
        '''
        Process that simply sends command "T0" to StimJims 1 and 2
        in a timely manner. Each phase is split to allow PAUSE button.
        '''
        current_timestamp = time.time()

        # Check if we have reached the defined stimulation count. If so, return immediately.
        if self._stim_index >= self.STIM_INSTANCE_COUNT:
            return

        # First phase, first StimJim is activated (StimJim 1 "Brain")
        if self._stim_phase == "STIM1":

            # Set the timestamp to the current time.
            self._stim_phase_timestamp = current_timestamp

            # Check so that "T0" will only be sent if stimjim is actually connected
            if (self._check_stimjim_availability(0)):
                # Display a message: "Stim iteration #n - StimJim 1".
                message: SessionMessage = SessionMessage(f"Stim iteration #{self._stim_index + 1} - StimJim 1")
                self.signals.new_message.emit(message)

                # Send the activation command to stimjim[0], which is StimJim 1 "Brain".
                ApplicationConfiguration.stimjim[0].send_command("T0")

            # If no stimjim connected, justdisplay a message
            else:
                # Display a message: "StimJim not found. Virtual stimulation: Stim iteration #n - StimJim 1".
                message: SessionMessage = SessionMessage(f"StimJim not found. Virtual stimulation: Stim iteration #{self._stim_index + 1} - StimJim 1")
                self.signals.new_message.emit(message)

            # Copy data into the demo data object
            self.demo_data = np.concatenate([self.demo_data, data])

            # Set phase to next.
            self._stim_phase = "WAIT_GAP"

        # Second phase, simply a wait time between StimJim 1 and 2.
        elif self._stim_phase == "WAIT_GAP":

            # Copy data into the demo data object
            self.demo_data = np.concatenate([self.demo_data, data])
            
            # Check if STIM_GAP_MILLISECONDS have elapsed since the timestamp of previous phase.
            if current_timestamp - self._stim_phase_timestamp >= self.STIM_GAP_MILLISECONDS / 1000.0:
                # Set phase to next.
                self._stim_phase = "STIM2"

        # Third phase, second StimJim is activated (StimJim 2 "Nerve")
        elif self._stim_phase == "STIM2":

            # Set the timestamp to the current time.
            self._stim_phase_timestamp = current_timestamp

            # Check so that "T0" will only be sent if stimjim is actually connected
            if (self._check_stimjim_availability(1)):
                # Display a message: "Stim iteration #n - StimJim 2"
                message: SessionMessage = SessionMessage(f"Stim iteration #{self._stim_index + 1} - StimJim 2")
                self.signals.new_message.emit(message)

                # Send the activation command to stimjim[1], which is StimJim 2 "Nerve".
                ApplicationConfiguration.stimjim[1].send_command("T0")

            else:
                # Display a message: "StimJim not found. Virtual stimulation: Stim iteration #n - StimJim 2"
                message: SessionMessage = SessionMessage(f"StimJim not found. Virtual stimulation: Stim iteration #{self._stim_index + 1} - StimJim 2")
                self.signals.new_message.emit(message)

            # Copy data into the demo data object
            self.demo_data = np.concatenate([self.demo_data, data])

            # Set phase to next
            self._stim_phase = "WAIT_LONG"

        # Last phase, simply a wait time between the stimulation iterations. Typically 3-5 seconds.
        elif self._stim_phase == "WAIT_LONG":
            
            # Check if STIM_INTERVAL_SECONDS have elapsed since the timestamp of previous phase.
            if current_timestamp - self._stim_phase_timestamp >= self.STIM_INTERVAL_SECONDS:
                # Increase stimulation iteration count by 1.
                self._stim_index += 1
                # Reset the phase to STIM1.
                self._stim_phase = "STIM1"

                # Save the data for the two stimulations
                self.save(self._fid)

                # Display a message if all stimulation iterations are complete.
                if self._stim_index >= self.STIM_INSTANCE_COUNT:
                    self.signals.new_message.emit(SessionMessage("All stimulations completed."))

    def finalize (self) -> None:        
        if (self._fid is not None):
            #Close the data file for this session
            self._fid.close()

    #endregion

    #region Private

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

            pass

    def _check_stimjim_availability(self, index: int) -> bool:
        stimjim_list = ApplicationConfiguration.stimjim
        if (index < len(stimjim_list) and stimjim_list[index] is not None):
            return True
        else:
            return False

    #endregion
