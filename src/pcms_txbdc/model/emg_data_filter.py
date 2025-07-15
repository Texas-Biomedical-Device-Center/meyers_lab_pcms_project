import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi

class EmgDataFilter:

    #region Constants

    ORDER = 2
    CUTOFF_FREQ_MIN = 100
    CUTOFF_FREQ_MAX = 1000
    FS = 5000

    #endregion

    #region Non-Constants

    sos = None
    filter_state = None

    #endregion

    #region Static methods

    def initialize_filter () -> None:

        EmgDataFilter.sos = butter(
            EmgDataFilter.ORDER, 
            [EmgDataFilter.CUTOFF_FREQ_MIN, EmgDataFilter.CUTOFF_FREQ_MAX],
            btype='bandpass',
            output='sos',
            fs = EmgDataFilter.FS)
        
        EmgDataFilter.filter_state = sosfilt_zi(EmgDataFilter.sos)

        pass

    def filter (data: np.ndarray) -> np.ndarray:
        
        #Calculate the filtered data and the new filter state
        filtered_data, filter_state = sosfilt(EmgDataFilter.sos, data, zi = EmgDataFilter.filter_state)

        #Set the filter state
        EmgDataFilter.filter_state = filter_state

        #Return the filtered data
        return filtered_data

    #endregion