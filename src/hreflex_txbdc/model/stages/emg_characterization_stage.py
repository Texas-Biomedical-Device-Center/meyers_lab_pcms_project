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

class EmgCharacterizationStage (Stage):

    #region Constants

    #This defines the duration of an individual bin in miliseconds
    BIN_DURATION_MILLISECONDS: int = 50

    #This defines the number of samples for an individual bin
    #This is: (sample rate / 1000) * BIN_DURATION_MILLISECONDS
    BIN_DURATION_SAMPLE_COUNT: int = 250

    #The minimum duration for which we will scan for trial initiation criteria to be met
    TRIAL_INITIATION_PHASE_MIN_DURATION_MILLISECONDS: int = 2200

    #The maximum duration for which we will scan for trial initiation criteria to be met
    TRIAL_INITIATION_PHASE_MAX_DURATION_MILLISECONDS: int = 2700

    #The minimum and maximum range for trial initiation
    TRIAL_INITIATION_MIN_RANGE_MICROVOLTS: float = 15.0
    TRIAL_INITIATION_MAX_RANGE_MICROVOLTS: float = 300.0

    #endregion

    #region Constructor

    def __init__(self):
        super().__init__()

        #Set the basic stage information
        self.stage_name = "S1"
        self.stage_description = "EMG Characterization"
        self.stage_type = Stage.STAGE_TYPE_EMG_CHARACTERIZATION

        #Declare a variable to hold the monitored signal
        self._monitored_signal: np.ndarray = np.zeros(1)

        #Declare a variable to hold the bins
        self._bins: np.ndarray = np.zeros(1)

        #Declare a variable to hold the current monitored signal duration
        self._monitored_signal_duration_seconds: float = 0.0

        #Declare a variable to hold the number of samples that we will 
        #store in the monitored signal
        self._monitored_signal_sample_count: int = 0

        #Declare a variable that helps us determine whether we have streamed enough samples
        self._current_trial_sample_count: int = 0

        #Declare a variable to hold the trial state
        self._is_trial_set_up: bool = False

        #Declare a variable to hold the mean of each trial
        self._trial_means: list[float] = []

        #Instantiate a random-number generator and use the current time as a seed
        self._rng: Random = Random(datetime.now().timestamp())

        #Create a private variable that will be used to store a save-file handle
        self._fid: BinaryIO = None

    #endregion

    #region Overrides

    def initialize (self, subject_id: str) -> tuple[bool, str]:
        #Set the subject id
        self._subject_id: str = subject_id

        #Set the "is trial set up" flag to false
        self._is_trial_set_up = False

        #Set the current trial sample count to 0
        self._current_trial_sample_count = 0

        #Clear the list of trial means
        self._trial_means.clear()

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
        
        #Check to see if there is an existing hrs1 file for this subject.
        files_list: list[str] = os.listdir(file_path)
        for f in files_list:
            if (f.endswith("hrs1")):
                #If we find an existing hrs1 file for this subject, then it means this subject has already completed
                #this stage. Let's return False with an informative message to the user.
                return (False, "This subject has already completed this stage. EMG Characterization data exists for this subject. This stage cannot proceed. If this is an issue, please talk to your PI.")

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

        #Check to see if we need to set up a new trial
        if (not self._is_trial_set_up):
            #Set up a new trial
            self._setup_new_trial()

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
                bin_start = EmgCharacterizationStage.BIN_DURATION_SAMPLE_COUNT * bin_index
                bin_end = EmgCharacterizationStage.BIN_DURATION_SAMPLE_COUNT * (bin_index + 1)

                if (bin_end > len(self._monitored_signal)):
                    bin_end = len(self._monitored_signal)

                bin_mean: float = np.mean(self._monitored_signal[bin_start:bin_end])
                self._bins[bin_index] = bin_mean
            
            #Get the mean of all the bins
            bin_grand_mean: float = np.mean(self._bins)

            #If the bin grand mean is within a pre-specified min or max range, then
            #we consider this a trial initiation.
            if ((self._current_trial_sample_count >= self._monitored_signal_sample_count) and
                (bin_grand_mean >= EmgCharacterizationStage.TRIAL_INITIATION_MIN_RANGE_MICROVOLTS) and 
                (bin_grand_mean <= EmgCharacterizationStage.TRIAL_INITIATION_MAX_RANGE_MICROVOLTS)):

                #A trial has been initiatied...

                #Add the grand mean to the list of trial means
                self._trial_means.append(bin_grand_mean)

                #Save the trial to the data file
                self._save_trial(bin_grand_mean)

                #Update the session plot
                self._update_session_plot()

                #Update the trial plot
                self._update_trial_plot(bin_grand_mean)

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

    def get_trial_plot_options (self) -> list[str]:
        return ["Most recent trial"]
    
    def get_session_plot_options (self) -> list[str]:
        return ["Session history"]

    def update_trial_plot (self) -> None:
        #This stage will not support updating the plots from an external call.
        pass

    def update_session_plot (self) -> None:
        #This stage will not support updating the plots from an external call.
        pass

    #endregion

    #region Private methods

    def _setup_new_trial (self) -> None:
        #Choose a trial-initiation monitoring duration
        dur_milliseconds: int = self._rng.randint(
            EmgCharacterizationStage.TRIAL_INITIATION_PHASE_MIN_DURATION_MILLISECONDS,
            EmgCharacterizationStage.TRIAL_INITIATION_PHASE_MAX_DURATION_MILLISECONDS
        )

        #Round the number to the nearest 50-ms
        dur_milliseconds = self._round_special(dur_milliseconds, 50)

        #Convert to seconds
        self._monitored_signal_duration_seconds = float(dur_milliseconds) / 1000.0

        #Set the number of samples that we care about
        self._monitored_signal_sample_count = int(self._monitored_signal_duration_seconds * Stage.SAMPLE_RATE)

        #Get the number of bins we will be collecting
        bin_count: int = int(dur_milliseconds / EmgCharacterizationStage.BIN_DURATION_MILLISECONDS)

        #Re-size the appropriate arrays to hold the data we care about
        self._monitored_signal = np.zeros(self._monitored_signal_sample_count)
        self._bins = np.zeros(bin_count)

        #Set the flag indicating that the trial has been set up
        self._is_trial_set_up = True

        #We are done. return from this function.
        return

    def _round_special (self, x: int, base: int = 50) -> int:
        return base * int(round(float(x) / float(base)))

    def _update_session_plot (self) -> None:

        #Clear the plot
        self._session_widget.clear()

        #Plot the trial means
        self._session_widget.plot(range(0, len(self._trial_means)), self._trial_means, pen = None, symbol = 'o', symbolBrush=('b'), symbolSize=12)

        pass

    def _update_trial_plot (self, bin_grand_mean: float) -> None:
        #Clear the plot
        self._trial_widget.clear()

        #Plot the "raw" (absolute-valued) EMG data for this trial
        pen = pg.mkPen(color=(0, 0, 0))
        self._trial_widget.plot(range(0, len(self._monitored_signal)), self._monitored_signal, pen = pen)

        #Plot the binned data
        pen = pg.mkPen(color=(255, 0, 0), width = 2.0)
        xvals = list(range(0, len(self._bins)))
        for i in range(0, len(xvals)):
            xvals[i] *= EmgCharacterizationStage.BIN_DURATION_SAMPLE_COUNT
        self._trial_widget.plot(xvals, self._bins, pen = pen)

        # Get the ViewBox object
        view_box = self._trial_widget.getPlotItem().getViewBox()

        # Get the Y-axis limits
        y_min, y_max = view_box.viewRange()[1]

        #Plot the grand mean
        text_item = pg.TextItem(f"Mean = {bin_grand_mean:.2f}", anchor = (0, 0), color = (0, 0, 0))
        self._trial_widget.addItem(text_item)
        text_item.setPos(0, y_max)

        pass

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
            FileIO_Helpers.write(self._fid, "float64", EmgCharacterizationStage.TRIAL_INITIATION_MIN_RANGE_MICROVOLTS)
            FileIO_Helpers.write(self._fid, "float64", EmgCharacterizationStage.TRIAL_INITIATION_MAX_RANGE_MICROVOLTS)

            #Save the min and max recording duration for trial initiation criteria
            FileIO_Helpers.write(self._fid, "int32", EmgCharacterizationStage.TRIAL_INITIATION_PHASE_MIN_DURATION_MILLISECONDS)
            FileIO_Helpers.write(self._fid, "int32", EmgCharacterizationStage.TRIAL_INITIATION_PHASE_MAX_DURATION_MILLISECONDS)

            #Save the bin width
            FileIO_Helpers.write(self._fid, "int32", EmgCharacterizationStage.BIN_DURATION_MILLISECONDS)

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