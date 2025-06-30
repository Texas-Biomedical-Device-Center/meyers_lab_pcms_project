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

# from ..stimjim import StimJim
from am_systems_4100.am_systems_4100 import AmSystems4100

class SalineBathDemoDataStage(Stage):
    #region Constants

    # This defines the gap (ms) between Stimulator 1 and Stimulator 2 activation
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
        FileIO_Helpers.write_datetime(fid, self.current_datetime)

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
        self.current: float = None

        # Set up stimulator amplitude parameters
        self._amplitude_list = [Stage.STIM1_AMPLITUDE, Stage.STIM2_AMPLITUDE]

        for stim in enumerate(ApplicationConfiguration.stimulator):
            if (stim < len(ApplicationConfiguration.stimulator) and ApplicationConfiguration.stimulator is not None):
                amplitude = self._amplitude_list[stim]
                ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters(stim, amplitude)
            else:
                # Format and send the message
                message = SessionMessage(f"AM 4100 stimulator not found. Stage set up for testing without stimulator.")
                self._session_messages.append(message)
                self._update_session_messages()

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
        self.current_datetime: datetime = datetime.now()

        #Define the path where we will save data
        app_data_path: str = user_data_dir(ApplicationConfiguration.appname, ApplicationConfiguration.appauthor)
        file_path: str = os.path.join(app_data_path, self._subject_id)

        #Create the folder if it does not yet exist
        if (not os.path.exists(file_path)):
            os.makedirs(file_path)

        #Define a file name for the file to which we will save data
        file_timestamp: str = self.current_datetime.strftime("%Y%m%dT%H%M%S")
        file_name: str = f"{self._subject_id}_{file_timestamp}.pcms"

        #Open a file for saving data for this stage
        self._fid = open(os.path.join(file_path, file_name), "wb")

        #Save the file header for this data file
        self._save_file_header()

        #Return from this function
        return (True, "")

    def process(self, data: np.ndarray) -> None:
        '''
        Process that set_active and trigger_single for AM 4100 #1 and #2, or displays
        a message in a timely manner. Each phase is split to allow PAUSE button.
        '''
        current_timestamp = time.time()

        # Check if we have reached the defined stimulation count. If so, return immediately.
        if self._stim_index >= self.STIM_INSTANCE_COUNT:
            return

        # First phase, first AM 4100 stimulator is activated (AM 4100 #1 "Brain")
        if self._stim_phase == "STIM1":

            # Set the timestamp to the current time.
            self._stim_phase_timestamp = current_timestamp

            # Check if first AM 4100 is connected
            if (self._check_am_4100_availability(0)):
                # Display a message: "Stim iteration #n - AM 4100 #1".
                message: SessionMessage = SessionMessage(f"Stim iteration #{self._stim_index + 1} - AM 4100 #1")
                self.signals.new_message.emit(message)

                # Send the activation command to stimulator[0], which is AM 4100 #1 "Brain".
                stim = ApplicationConfiguration.stimulator[0]
                stim.set_active(True)
                stim.trigger_single()

            else:
                # Display a message: "Stimulator not found. Stim iteration #n - Stimulator #1".
                message: SessionMessage = SessionMessage(f"Stimulator not found. Stim iteration #{self._stim_index + 1} - Stimulator #1")
                self.signals.new_message.emit(message)

            # Copy data into the demo data object
            self.demo_data = np.concatenate([self.demo_data, data])

            # Set phase to next.
            self._stim_phase = "WAIT_GAP"

        # Second phase, simply a wait time between stimulators 1 and 2.
        elif self._stim_phase == "WAIT_GAP":

            # Copy data into the demo data object
            self.demo_data = np.concatenate([self.demo_data, data])
            
            # Check if STIM_GAP_MILLISECONDS have elapsed since the timestamp of previous phase.
            if current_timestamp - self._stim_phase_timestamp >= self.STIM_GAP_MILLISECONDS / 1000.0:
                # Set phase to next.
                self._stim_phase = "STIM2"

        # Third phase, second AM 4100 is activated (AM 4100 #2 "Nerve")
        elif self._stim_phase == "STIM2":

            # Set the timestamp to the current time.
            self._stim_phase_timestamp = current_timestamp

            # Check if second AM 4100 is connected
            if (self._check_am_4100_availability(1)):
                # Display a message: "Stim iteration #n - AM 4100 #2"
                message: SessionMessage = SessionMessage(f"Stim iteration #{self._stim_index + 1} - AM 4100 #2")
                self.signals.new_message.emit(message)

                # Send the activation command to stimulator[1], which is AM 4100 #2 "Nerve".
                stim = ApplicationConfiguration.stimulator[1]
                stim.set_active(True)
                stim.trigger_single()

            else:
                # Display a message: "Stimulator not found. Stim iteration #n - Stimulator #2"
                message: SessionMessage = SessionMessage(f"Stimulator not found. Stim iteration #{self._stim_index + 1} - Stimulator #2")
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

                    # Emit signal to the main window to indicate session completion
                    self.signals.session_complete.emit()
        
        return

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

    def _check_am_4100_availability(self, index: int) -> bool:
        am_4100_list = ApplicationConfiguration.stimulator
        if (index < len(am_4100_list) and am_4100_list[index] is not None):
            return True
        else:
            return False

    #endregion
