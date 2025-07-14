import numpy as np
import time
import os
from datetime import datetime
from platformdirs import user_data_dir

from .stage import Stage
from ..session_message import SessionMessage
from ..application_configuration import ApplicationConfiguration
from ..fileio_helpers import FileIO_Helpers


class SalineBathDemoDataStage(Stage):
    STIM_GAP_MILLISECONDS = 100.0
    STIM_INTERVAL_SECONDS = 5.0
    STIM_INSTANCE_COUNT = 5

    def __init__(self):
        super().__init__()
        self.stage_name = "S0"
        self.stage_description = "Saline Bath Demo Data"
        self.stage_type = Stage.STAGE_TYPE_SALINE_DEMO_DATA
        self._fid = None
        self.demo_data = np.zeros(1)
        self._stim_index = 0
        self._stim_phase = "STIM1"
        self._amplitude_list = [Stage.STIM1_AMPLITUDE, Stage.STIM2_AMPLITUDE]
        self._stim_phase_timestamp = None
        self.current_datetime = datetime.now()

    def initialize(self, subject_id):
        self._subject_id = subject_id
        self._stim_index = 0
        self._stim_phase = "STIM1"

        for i, stim in enumerate(ApplicationConfiguration.stimulator):
            if stim is not None:
                ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters(i, self._amplitude_list[i])
            else:
                self.signals.new_message.emit(SessionMessage(f"Stimulator #{i} not found."))

        app_data_path = user_data_dir(ApplicationConfiguration.appname, ApplicationConfiguration.appauthor)
        file_path = os.path.join(app_data_path, subject_id)
        os.makedirs(file_path, exist_ok=True)
        file_name = f"{subject_id}_{self.current_datetime.strftime('%Y%m%dT%H%M%S')}.pcms"
        self._fid = open(os.path.join(file_path, file_name), "wb")
        self._save_file_header()
        return True, ""

    def process(self, data):
        current_time = time.time()

        if self._stim_index >= self.STIM_INSTANCE_COUNT:
            return

        if self._stim_phase == "STIM1":
            self._stim_phase_timestamp = current_time
            stim = ApplicationConfiguration.stimulator[0]
            if stim:
                stim.set_active(True)
                stim.trigger_single()
                self.signals.new_message.emit(SessionMessage(f"Stim #{self._stim_index + 1} - AM 4100 #1"))
            self.demo_data = np.concatenate([self.demo_data, data])
            self._stim_phase = "WAIT_GAP"

        elif self._stim_phase == "WAIT_GAP":
            self.demo_data = np.concatenate([self.demo_data, data])
            if current_time - self._stim_phase_timestamp >= self.STIM_GAP_MILLISECONDS / 1000.0:
                self._stim_phase = "STIM2"

        elif self._stim_phase == "STIM2":
            self._stim_phase_timestamp = current_time
            stim = ApplicationConfiguration.stimulator[1]
            if stim:
                stim.set_active(True)
                stim.trigger_single()
                self.signals.new_message.emit(SessionMessage(f"Stim #{self._stim_index + 1} - AM 4100 #2"))
            self.demo_data = np.concatenate([self.demo_data, data])
            self._stim_phase = "WAIT_LONG"

        elif self._stim_phase == "WAIT_LONG":
            if current_time - self._stim_phase_timestamp >= self.STIM_INTERVAL_SECONDS:
                self._stim_index += 1
                self._stim_phase = "STIM1"
                self.save(self._fid)
                if self._stim_index >= self.STIM_INSTANCE_COUNT:
                    self.signals.new_message.emit(SessionMessage("All stimulations completed."))
                    self.signals.session_complete.emit()

    def save(self, fid):
        FileIO_Helpers.write(fid, "int32", 1)
        FileIO_Helpers.write_datetime(fid, self.current_datetime)
        for val in self.demo_data:
            FileIO_Helpers.write(fid, "float64", val)

    def finalize(self):
        if self._fid:
            self._fid.close()

    def _save_file_header(self):
        FileIO_Helpers.write(self._fid, "int32", 0)
        FileIO_Helpers.write_string(self._fid, self._subject_id)
        FileIO_Helpers.write_datetime(self._fid, datetime.now())
        FileIO_Helpers.write_string(self._fid, self.stage_name)
        FileIO_Helpers.write_string(self._fid, self.stage_description)
        FileIO_Helpers.write(self._fid, "int32", self.stage_type)


class Stage0aFWaveLatency(Stage):
    def __init__(self):
        super().__init__()
        self.stage_name = "Stage 0a: F-wave Latency and PCT"
        self.stage_description = "Stimulate Nerve repeatedly to collect EMG for F-wave and PCT"
        self.stage_type = Stage.STAGE_TYPE_EMG_CHARACTERIZATION
        self._fid = None
        self._trial_index = 0
        self._interval_sec = 5
        self._max_trials = 10
        self._start_time = None

    def initialize(self, subject_id):
        self._subject_id = subject_id
        self._trial_index = 0
        ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters(1, amplitude_ma=0.8)
        self._start_time = time.time()
        self._next_stim_time = self._start_time
        dt = datetime.now()
        self._current_datetime = dt
        app_data_path = user_data_dir(ApplicationConfiguration.appname, ApplicationConfiguration.appauthor)
        file_path = os.path.join(app_data_path, subject_id)
        os.makedirs(file_path, exist_ok=True)
        file_name = f"{subject_id}_{dt.strftime('%Y%m%dT%H%M%S')}_fwave0a.pcms"
        self._fid = open(os.path.join(file_path, file_name), "wb")
        self._save_file_header()
        self.signals.new_message.emit(SessionMessage("Beginning Stage 0a: F-wave Latency"))
        return True, ""

    def process(self, data):
        current_time = time.time()
        if self._trial_index >= self._max_trials:
            self.signals.new_message.emit(SessionMessage("→ Stage 0a complete."))
            self.signals.session_complete.emit()
            return
        if current_time >= self._next_stim_time:
            stim = ApplicationConfiguration.stimulator[1]
            stim.set_active(True)
            stim.trigger_single()
            elapsed_time = current_time - self._start_time
            FileIO_Helpers.write(self._fid, "int32", self._trial_index + 1)
            FileIO_Helpers.write(self._fid, "float64", elapsed_time)
            for val in data:
                FileIO_Helpers.write(self._fid, "float64", val)
            self._trial_index += 1
            self._next_stim_time += self._interval_sec
            self.signals.new_message.emit(SessionMessage(f"Trial {self._trial_index}: Nerve Stim triggered"))

    def finalize(self):
        if self._fid:
            self._fid.close()

    def _save_file_header(self):
        FileIO_Helpers.write(self._fid, "int32", 1)
        FileIO_Helpers.write_string(self._fid, self._subject_id)
        FileIO_Helpers.write_datetime(self._fid, self._current_datetime)
        FileIO_Helpers.write_string(self._fid, self.stage_name)
        FileIO_Helpers.write_string(self._fid, self.stage_description)
        FileIO_Helpers.write(self._fid, "int32", self.stage_type)


class Stage0bMEPLatency(Stage0aFWaveLatency):
    def __init__(self):
        super().__init__()
        self.stage_name = "Stage 0b: MEP Latency and CCT"
        self.stage_description = "Stimulate Brain repeatedly to collect EMG for MEP and CCT"

    def initialize(self, subject_id):
        self._subject_id = subject_id
        self._trial_index = 0
        ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters(0, amplitude_ma=0.8)
        self._start_time = time.time()
        self._next_stim_time = self._start_time
        dt = datetime.now()
        self._current_datetime = dt
        app_data_path = user_data_dir(ApplicationConfiguration.appname, ApplicationConfiguration.appauthor)
        file_path = os.path.join(app_data_path, subject_id)
        os.makedirs(file_path, exist_ok=True)
        file_name = f"{subject_id}_{dt.strftime('%Y%m%dT%H%M%S')}_mep0b.pcms"
        self._fid = open(os.path.join(file_path, file_name), "wb")
        self._save_file_header()
        self.signals.new_message.emit(SessionMessage("Beginning Stage 0b: MEP Latency"))
        return True, ""

    def process(self, data):
        current_time = time.time()
        if self._trial_index >= self._max_trials:
            self.signals.new_message.emit(SessionMessage("→ Stage 0b complete."))
            self.signals.session_complete.emit()
            return
        if current_time >= self._next_stim_time:
            stim = ApplicationConfiguration.stimulator[0]
            stim.set_active(True)
            stim.trigger_single()
            elapsed_time = current_time - self._start_time
            FileIO_Helpers.write(self._fid, "int32", self._trial_index + 1)
            FileIO_Helpers.write(self._fid, "float64", elapsed_time)
            for val in data:
                FileIO_Helpers.write(self._fid, "float64", val)
            self._trial_index += 1
            self._next_stim_time += self._interval_sec
            self.signals.new_message.emit(SessionMessage(f"Trial {self._trial_index}: Brain Stim triggered"))


class PCMSConditioningStage(Stage):
    def __init__(self, name: str, description: str, interval_sec: float, duration_min: float, stim_indices: list[int]):
        super().__init__()
        self.stage_name = name
        self.stage_description = description
        self.stage_type = Stage.STAGE_TYPE_CONDITIONING
        self._fid = None
        self._trial_index = 0
        self._interval_sec = interval_sec
        self._duration_min = duration_min
        self._stim_indices = stim_indices
        self._start_time = None

    def initialize(self, subject_id):
        self._subject_id = subject_id
        self._trial_index = 0

        for i in self._stim_indices:
            ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters(i, amplitude_ma=0.8)

        dt = datetime.now()
        self._current_datetime = dt
        app_data_path = user_data_dir(ApplicationConfiguration.appname, ApplicationConfiguration.appauthor)
        file_path = os.path.join(app_data_path, subject_id)
        os.makedirs(file_path, exist_ok=True)
        file_name = f"{subject_id}_{dt.strftime('%Y%m%dT%H%M%S')}_pcms.pcms"
        self._fid = open(os.path.join(file_path, file_name), "wb")
        self._save_file_header()

        self._start_time = time.time()
        self._end_time = self._start_time + self._duration_min * 60
        self._next_stim_time = self._start_time

        self.signals.new_message.emit(SessionMessage(f"Beginning: {self.stage_name}"))
        return True, ""

    def process(self, data):
        current_time = time.time()

        if current_time >= self._end_time:
            self.signals.new_message.emit(SessionMessage(f"→ {self.stage_name} complete."))
            self.signals.session_complete.emit()
            return

        if current_time >= self._next_stim_time:
            for i in self._stim_indices:
                stim = ApplicationConfiguration.stimulator[i]
                stim.set_active(True)
                stim.trigger_single()
                time.sleep(0.01)

            self._trial_index += 1
            elapsed_time = current_time - self._start_time
            FileIO_Helpers.write(self._fid, "int32", self._trial_index)
            FileIO_Helpers.write(self._fid, "float64", elapsed_time)

            self.signals.new_message.emit(SessionMessage(
                f"Trial {self._trial_index}: Stim indices {self._stim_indices} triggered at {elapsed_time:.2f} sec"
            ))
            self._next_stim_time += self._interval_sec

    def finalize(self):
        if self._fid:
            self._fid.close()

    def _save_file_header(self):
        FileIO_Helpers.write(self._fid, "int32", 1)
        FileIO_Helpers.write_string(self._fid, self._subject_id)
        FileIO_Helpers.write_datetime(self._fid, self._current_datetime)
        FileIO_Helpers.write_string(self._fid, self.stage_name)
        FileIO_Helpers.write_string(self._fid, self.stage_description)
        FileIO_Helpers.write(self._fid, "int32", self.stage_type)
