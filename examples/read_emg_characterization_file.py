# %% Imports

from typing import BinaryIO
from platformdirs import user_data_dir
import os
import numpy as np

from pcms_txbdc.model.application_configuration import ApplicationConfiguration
from pcms_txbdc.model.emg_characterization_data import EmgCharacterizationData, EmgCharacterizationHeader, EmgCharacterizationTrial

# %% Define the subject ID and then find all EMG characterization stage data files

subject_id: str = "TEST"

file_list: list[str] = EmgCharacterizationData.find_all_emg_characterization_data_files(subject_id)

# %% Print the list of files found

print(f"{len(file_list)} files were found: ")
for f in file_list:
    print(f)

# %% Print data from the first file that was found

if (len(file_list) > 0):

    app_data_path: str = user_data_dir(ApplicationConfiguration.appname, ApplicationConfiguration.appauthor)
    subject_data_path: str = os.path.join(app_data_path, subject_id)
    full_file_path: str = os.path.join(subject_data_path, file_list[0])

    session_data: EmgCharacterizationData = EmgCharacterizationData()
    
    fid: BinaryIO = open(full_file_path, "rb")
    session_data.read(fid)
    fid.close()

    #Display the number of trials
    print(f"Trial count = {len(session_data.trials)}")

    #Display the grand grand mean
    gm: list[float] = session_data.get_all_grandmeans()
    gm_mean: float = np.mean(gm)

    print(f"Grand mean = {gm_mean}")