from typing import Tuple
from PySide6.QtCore import QRunnable, Slot, Signal, QObject
import numpy as np
import time

from .open_ephys_streamer import OpenEphysStreamer

class BackgroundWorkerSignals (QObject):

    #region Signals

    data_received_signal = Signal(object)

    #endregion

class BackgroundWorker (QRunnable):
    '''
    Worker thread
    '''

    #region Constructor

    def __init__(self):
        super().__init__()

        #Public signals
        self.signals = BackgroundWorkerSignals()

        #Private members
        self._open_ephys_streamer = OpenEphysStreamer()
        self._should_cancel = False

    #endregion

    #region Methods

    def cancel (self):
        self._should_cancel = True

    @Slot()
    def run (self):
        '''
        This is the code executed by the background thread.
        '''

        #Initialize the open ephys streamer
        self._open_ephys_streamer.initialize()

        #Iterate until the "should cancel" is set to True
        while (not self._should_cancel):

            #Process any messages to/from OpenEphys
            result = self._open_ephys_streamer.callback()

            #Check to see if any data was received
            if (result is not None) and (result[0] is not None):
                self.signals.data_received_signal.emit(result)

        return

    #endregion

