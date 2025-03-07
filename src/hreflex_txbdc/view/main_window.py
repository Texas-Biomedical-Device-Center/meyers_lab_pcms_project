from PySide6.QtWidgets import (
    QMainWindow, 
    QLabel, 
    QVBoxLayout, 
    QWidget, 
    QHBoxLayout, 
    QPushButton, 
    QLineEdit, 
    QComboBox, 
    QSizePolicy,
    QFrame,
    QGridLayout,
    QPlainTextEdit,
    QMessageBox
)

from PySide6.QtGui import QFont
from PySide6.QtCore import QThreadPool
from PySide6 import QtCore
import pyqtgraph as pg
import numpy as np
import pandas as pd
import os
from datetime import datetime
from datetime import timedelta

from typing import Tuple

from ..model.background_worker import BackgroundWorker
from ..model.stages.stage import Stage
from ..model.stages.emg_characterization_stage import EmgCharacterizationStage
from ..model.stages.mh_recruitment_curve_stage import MhRecruitmentCurveStage
from ..model.session_message import SessionMessage
from ..model.application_configuration import ApplicationConfiguration

import serial

class MainWindow(QMainWindow):
    """
    Main application window for H-Reflex Conditioning with input fields for experimental variables
    and plots to visualize trial and live EMG data.
    """

    #region Constructor

    def __init__(self) -> None:
        super().__init__()

        # Initialize a variable to hold EMG signal data for plotting
        self._emg_signal_data = np.zeros(5000)
        self._emg_signal_data_max_length = 5000

        # Initialize a flag to track whether a session is currently running
        self._is_session_running: bool = False
        self._is_session_paused: bool = False

        # Initialize a list of stages
        self._stages: list[Stage] = []

        emg_characterization_stage: EmgCharacterizationStage = EmgCharacterizationStage()
        mh_recruitment_curve_stage: MhRecruitmentCurveStage = MhRecruitmentCurveStage()
        self._stages.append(emg_characterization_stage)
        self._stages.append(mh_recruitment_curve_stage)

        # Initialize the "selected stage"
        self._selected_stage: Stage = self._stages[0]

        # Initialize a variable to hold the subject name
        self._subject_name: str = ""

        # Initialize a set of messages that will be displayed in the session message box
        self._session_messages: list[SessionMessage] = []

        # Set up window title and size
        self.setWindowTitle("H-Reflex Conditioning")
        self.resize(900, 600)  # Increased the width of the window

        #Create some fonts that will be used for the ui elements
        self._regular_font: QFont = QFont("Arial", 12)
        self._bold_font: QFont = QFont("Arial", 12, QFont.Bold)
        self._large_bold_font: QFont = QFont("Arial", 20, QFont.Bold)

        # Main layout container
        self._layout: QGridLayout = QGridLayout()
        self._layout.setRowStretch(0, 0)
        self._layout.setRowStretch(1, 1)
        self._layout.setRowStretch(2, 1)
        self._layout.setRowStretch(3, 0)

        # Initialize layout sections
        self._create_top_section()
        self._create_middle_section()
        self._create_bottom_section()

        # Set the central widget for the main window layout
        central_widget = QWidget()
        central_widget.setLayout(self._layout)
        self.setCentralWidget(central_widget)

        # Initialize some debug variables
        self._frame_count: int = 0
        self._sample_count: int = 0
        self._min_sample_count: int = -1
        self._max_sample_count: int = -1
        self._frame_start = datetime.now()

        # Set the session and plot widgets on each stage
        for s in self._stages:
            s.set_session_and_trial_widgets(self._session_history_plot_widget, self._previous_trial_plot_widget)

        # Initialize the threadpool and the background worker
        self.threadpool = QThreadPool()
        self.background_worker = BackgroundWorker()
        self.background_worker.signals.data_received_signal.connect(self._on_data_received)
        self.threadpool.start(self.background_worker)

    #endregion

    #region Methods for creating the user interface

    def _create_top_section(self) -> None:
        """
        Creates the top section of the window, which contains UI elements
        for selecting the subject and the stage. There are also labels to
        display the booth number and information about the selected stage.
        """

        #Create the grid
        grid = QGridLayout()
        #grid.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        #Create a sub-grid on the left side for the subject and stage
        left_grid = QGridLayout()
        grid.addLayout(left_grid, 0, 0)

        #Subject label
        subject_label = QLabel("Subject: ")
        subject_label.setFont(self._bold_font) 
        left_grid.addWidget(subject_label, 0, 0)
        
        #Subject text entry
        self._subject_entry = QLineEdit("")
        self._subject_entry.setFont(self._regular_font)
        self._subject_entry.setFixedWidth(150)
        self._subject_entry.setStyleSheet("QLineEdit {color: #000000; background-color: #FFFFFF;}")

        self._subject_entry.editingFinished.connect(self._on_subject_name_edited)
        left_grid.addWidget(self._subject_entry, 0, 1)

        #Stage label
        stage_label = QLabel("Stage: ")
        stage_label.setFont(self._bold_font)
        left_grid.addWidget(stage_label, 1, 0)

        #Stage selection box
        self._stage_selection_box = QComboBox()
        self._stage_selection_box.setFixedWidth(300)
        self._stage_selection_box.setFont(self._regular_font)
        self._stage_selection_box.setStyleSheet("QComboBox {color: #000000; background-color: #FFFFFF;}")
        self._stage_selection_box.currentIndexChanged.connect(self._on_stage_selection_changed)
        left_grid.addWidget(self._stage_selection_box, 1, 1)

        #Populate the stage selection box
        stage_strings: list[str] = []
        for s in self._stages:
            stage_str: str = f"({s.stage_name}) {s.stage_description}"
            stage_strings.append(stage_str)
        
        self._stage_selection_box.addItems(stage_strings)

        #Create another sub-grid on the right side that will display stage information
        right_grid = QGridLayout()
        right_grid.setColumnStretch(0, 1)
        right_grid.setColumnStretch(1, 1)
        right_grid.setColumnStretch(2, 1)
        right_grid.setColumnStretch(3, 1)

        grid.addLayout(right_grid, 0, 1)

        #Create labels for the booth name
        booth = QLabel("Booth: ")
        booth.setFont(self._bold_font)
        right_grid.addWidget(booth, 0, 0)

        self._booth_label = QLabel("NA")
        self._booth_label.setFont(self._regular_font)
        right_grid.addWidget(self._booth_label, 0, 1)

        #Create labels for the stage's VNS information
        vns = QLabel("VNS: ")
        vns.setFont(self._bold_font)
        right_grid.addWidget(vns, 0, 2)

        self._vns_label = QLabel("NA")
        self._vns_label.setFont(self._regular_font)
        right_grid.addWidget(self._vns_label, 0, 3)

        #Create labels for the stage's H-Amp information
        h_amp = QLabel("H-Amp: ")
        h_amp.setFont(self._bold_font)
        right_grid.addWidget(h_amp, 1, 0)

        self._h_amp_label = QLabel("NA")
        self._h_amp_label.setFont(self._regular_font)
        right_grid.addWidget(self._h_amp_label, 1, 1)

        #Create labels for the stage's percentile information
        percent = QLabel("Percent: ")
        percent.setFont(self._bold_font)
        right_grid.addWidget(percent, 1, 2)

        self._percent_label = QLabel("NA")
        self._percent_label.setFont(self._regular_font)
        right_grid.addWidget(self._percent_label, 1, 3)

        #Add the primary grid to the layout object
        self._layout.addLayout(grid, 0, 0)

    def _create_middle_section(self) -> None:
        """
        Creates the middle section with two EMG data plots: one for individual trial EMG data
        and one for displaying the EMG values of the last 50 trials.
        """
        middle_grid = QGridLayout()
        middle_grid.setRowStretch(0, 0)
        middle_grid.setRowStretch(1, 1)
        middle_grid.setColumnStretch(0, 1)
        middle_grid.setColumnStretch(1, 1)
        middle_grid.setColumnStretch(2, 1)

        #Create labels for each plot
        self._session_history_plot_selection_box = QComboBox()
        self._session_history_plot_selection_box.setFont(self._regular_font)
        self._session_history_plot_selection_box.setStyleSheet("QComboBox {color: #808080; background-color: #F0F0F0;}")
        self._session_history_plot_selection_box.setEnabled(False)
        self._session_history_plot_selection_box.currentIndexChanged.connect(self._on_session_history_plot_selection_index_changed)

        if (self._selected_stage is not None):
            items: list[str] = self._selected_stage.get_session_plot_options()
            for i in items:
                self._session_history_plot_selection_box.addItem(i)
        
        self._most_recent_trial_plot_selection_box = QComboBox()
        self._most_recent_trial_plot_selection_box.setFont(self._regular_font)
        self._most_recent_trial_plot_selection_box.setStyleSheet("QComboBox {color: #808080; background-color: #F0F0F0;}")
        self._most_recent_trial_plot_selection_box.setEnabled(False)
        self._most_recent_trial_plot_selection_box.currentIndexChanged.connect(self._on_most_recent_trial_plot_selection_index_changed)

        if (self._selected_stage is not None):
            items: list[str] = self._selected_stage.get_trial_plot_options()
            for i in items:
                self._most_recent_trial_plot_selection_box.addItem(i)

        live_emg_label = QLabel("Live EMG signal")
        live_emg_label.setFont(self._bold_font)
        live_emg_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        #This plot widget will show the session history
        self._session_history_plot_widget = pg.PlotWidget()
        self._session_history_plot_widget.setBackground('w')
        
        #This plot will show the most recent trial
        self._previous_trial_plot_widget = pg.PlotWidget()
        self._previous_trial_plot_widget.setBackground('w')

        #This plot will show the live EMG data
        self._live_emg_graph_widget = pg.PlotWidget()
        self._initialize_live_emg_plot()

        # Add both plots to the middle layout
        #middle_grid.addWidget(history_plot_label, 0, 0)
        middle_grid.addWidget(self._session_history_plot_selection_box, 0, 0)
        middle_grid.addWidget(self._most_recent_trial_plot_selection_box, 0, 1)
        middle_grid.addWidget(live_emg_label, 0, 2)

        middle_grid.addWidget(self._session_history_plot_widget, 1, 0)
        middle_grid.addWidget(self._previous_trial_plot_widget, 1, 1)
        middle_grid.addWidget(self._live_emg_graph_widget, 1, 2)

        #Add this section to the window's layout
        self._layout.addLayout(middle_grid, 1, 0)

    def _create_bottom_section(self) -> None:
        """
        Creates the bottom section with a message box and buttons for the user to start/stop the session
        and also to deliver feeds to the animal.
        """

        #Create the bottom layout as a grid
        bottom_layout: QGridLayout = QGridLayout()
        bottom_layout.setColumnStretch(0, 1)
        bottom_layout.setColumnStretch(1, 0)
        bottom_layout.setRowStretch(0, 0)
        bottom_layout.setRowStretch(1, 1)

        #Create a grid for the message box and command box
        message_command_layout: QGridLayout = QGridLayout()
        message_command_layout.setRowStretch(0, 1)
        message_command_layout.setRowStretch(1, 0)

        #Create a label for the session message box
        session_message_box_label = QLabel("Session messages")
        session_message_box_label.setFont(self._bold_font)
        session_message_box_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        #Command entry
        self._command_entry = QLineEdit("")
        self._command_entry.setFont(self._regular_font)
        self._command_entry.setPlaceholderText("Enter a command...")
        self._command_entry.setStyleSheet("QLineEdit {color: #000000; background-color: #FFFFFF;}")
        self._command_entry.returnPressed.connect(self._on_user_command_entered)
        
        #Create a session message box
        self._session_message_box = QPlainTextEdit()
        self._session_message_box.setFont(self._regular_font)
        self._session_message_box.setReadOnly(True)

        #Create 3 buttons: start/stop, pause, and feed
        self._start_stop_button = QPushButton("Start")
        self._start_stop_button.setFont(self._large_bold_font)
        self._start_stop_button.setFixedWidth(200)
        self._start_stop_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self._start_stop_button.setStyleSheet('QPushButton {color: #9D9D9D;}')
        self._start_stop_button.setEnabled(False)
        self._start_stop_button.clicked.connect(self._on_start_stop_button_clicked)

        self._pause_button = QPushButton("Pause")
        self._pause_button.setFont(self._large_bold_font)
        self._pause_button.setFixedWidth(200)
        self._pause_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self._pause_button.setEnabled(False)
        self._pause_button.clicked.connect(self._on_pause_button_clicked)

        self._feed_button = QPushButton("Feed")
        self._feed_button.setFont(self._large_bold_font)
        self._feed_button.setFixedWidth(200)
        self._feed_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self._feed_button.setEnabled(False)

        #Create a grid layout to hold the buttons
        button_layout = QGridLayout()
        button_layout.setRowStretch(0, 1)
        button_layout.setRowStretch(1, 1)
        button_layout.setRowStretch(2, 1)

        #Add the buttons to the button layout
        button_layout.addWidget(self._start_stop_button, 0, 0)
        button_layout.addWidget(self._pause_button, 1, 0)
        button_layout.addWidget(self._feed_button, 2, 0)

        #Add the message box and command box to the message command layout
        message_command_layout.addWidget(self._session_message_box, 0, 0)
        message_command_layout.addWidget(self._command_entry, 1, 0)
        
        #Add the session message box to the bottom layout
        bottom_layout.addWidget(session_message_box_label, 0, 0)
        bottom_layout.addLayout(message_command_layout, 1, 0)

        #Add the button layout to the bottom layout
        bottom_layout.addLayout(button_layout, 0, 1, 2, 1)

        #Add the bottom layout to the primary grid layout
        self._layout.addLayout(bottom_layout, 2, 0)

        pass

    #endregion

    #region Overrides

    def closeEvent(self, event):
        '''
        This method is called when the user attempts to close the application window.
        This method handles gracefully shutting the application down.
        '''

        #Disconnect from the data received signal
        self.background_worker.signals.data_received_signal.disconnect(self._on_data_received)

        #Shut down the background thread
        self.background_worker.cancel()

        #Close the StimJim serial connection if it exists
        ApplicationConfiguration.disconnect_from_stimjim()

        #Accept the event
        event.accept()

    #endregion

    #region Event handlers

    def _on_subject_name_edited (self) -> None:
        '''
        This method handles input of the subject name by the user. It filters
        the subject name so that it fits the criteria for subject names, and then
        sets the text on the subject entry field to be the validated text.
        '''

        #Get the text entered by the user
        current_text: str = self._subject_entry.text()

        #Filter the string so it only contains the following allowed characters:
        #   1. Alphanumeric characters
        #   2. Hyphens or underscores
        #All other character, including whitespace characters, will be removed.
        current_text = ''.join([
            c if (c.isalnum() or c == '-' or c == '_') else '' for c in current_text
        ])

        #Now change the string to all uppercase characters, and set the subject name private variable.
        self._subject_name = current_text.upper()

        #Now set the text on the text entry to the updated subject name
        self._subject_entry.setText(self._subject_name)

        #Check to see if the start/stop button should be enabled
        if (len(self._subject_entry.text()) > 0) and (self._selected_stage is not None):
            #If so...

            #Enable the start/stop button
            self._start_stop_button.setEnabled(True)
            self._start_stop_button.setStyleSheet('QPushButton {color: green;}')
        else:
            #If not...

            #Disable the start/stop button
            self._start_stop_button.setEnabled(False)
            self._start_stop_button.setStyleSheet('QPushButton {color: #9D9D9D;}')

    def _on_stage_selection_changed (self) -> None:
        '''
        This function is executed anytime the user selects a stage
        in the stage selection box.
        '''

        #Set the selected stage
        current_stage_index = self._stage_selection_box.currentIndex()
        if (current_stage_index >= 0):
            self._selected_stage = self._stages[current_stage_index]
        else:
            self._selected_stage = None
        
        #Re-populate the session plot selection combo box and the trial plot selection combo box
        if (self._selected_stage is not None):
            items: list[str] = self._selected_stage.get_session_plot_options()

            self._session_history_plot_selection_box.clear()
            for i in items:
                self._session_history_plot_selection_box.addItem(i)

            items: list[str] = self._selected_stage.get_trial_plot_options()

            self._most_recent_trial_plot_selection_box.clear()
            for i in items:
                self._most_recent_trial_plot_selection_box.addItem(i)

        #Check to see if the start/stop button should be enabled
        if (len(self._subject_entry.text()) > 0) and (self._selected_stage is not None):
            #If so...

            #Enable the start/stop button
            if (hasattr(self, "_start_stop_button")) and (self._start_stop_button is not None):
                self._start_stop_button.setEnabled(True)
                self._start_stop_button.setStyleSheet('QPushButton {color: green;}')
        else:
            #If not...

            #Disable the start/stop button
            if (hasattr(self, "_start_stop_button")) and (self._start_stop_button is not None):
                self._start_stop_button.setEnabled(False)
                self._start_stop_button.setStyleSheet('QPushButton {color: #9D9D9D;}')

    def _on_data_received (self, received: Tuple[np.ndarray, float]) -> None:
        #Grab the data was sent from Open Ephys
        data = received[0]
        sample_rate = received[1]

        #Append the new data to the live EMG signal array, and remove old data
        self._emg_signal_data = np.concatenate([self._emg_signal_data, data])
        if (len(self._emg_signal_data) > self._emg_signal_data_max_length):
            elements_to_remove = len(self._emg_signal_data) - self._emg_signal_data_max_length
            self._emg_signal_data = self._emg_signal_data[elements_to_remove:]
        
        #For debugging purposes, keep a count of how many frames per second we are achieving
        self._frame_count += 1
        self._sample_count += len(data)

        if (self._min_sample_count == -1) or (len(data) < self._min_sample_count):
            self._min_sample_count = len(data)
        
        if (self._max_sample_count == -1) or (len(data) > self._max_sample_count):
            self._max_sample_count = len(data)
        
        current_time = datetime.now()
        if (current_time >= (self._frame_start + timedelta(seconds=1))):
            samples_per_frame = self._sample_count / self._frame_count
            print(f"Frame count = {self._frame_count}, Sample count = {self._sample_count}, Samples per frame = {samples_per_frame}, Min samples per frame = {self._min_sample_count}, Max samples per frame = {self._max_sample_count}, Sample rate = {sample_rate}")
            self._min_sample_count = -1
            self._max_sample_count = -1
            self._frame_start = current_time
            self._frame_count = 0
            self._sample_count = 0
        
        #Check to see if a session is actively running
        if (self._is_session_running) and (not (self._is_session_paused)):
            #If so, process the data through the selected stage
            self._selected_stage.process(data)

        #Plot the live emg data
        self._plot_live_emg()

        #Return from this function
        return

    def _on_start_stop_button_clicked (self) -> None:
        if (not self._is_session_running):
            #Clear the list of messages
            self._clear_session_messages()

            #Subscribe to signals from the selected stage
            self._selected_stage.signals.new_message.connect(self._on_message_received_from_stage)

            #Initialize the selected stage
            init_result: tuple[bool, str] = self._selected_stage.initialize(self._subject_name)

            #Check to see if the stage can proceed
            if (not init_result[0]):
                #Disconnect from the signals of the selected stage
                self._selected_stage.signals.new_message.disconnect(self._on_message_received_from_stage)

                #If not, then display an error dialog box to the user
                error_message: str = init_result[1]

                dlg: QMessageBox = QMessageBox(self)
                dlg.setWindowTitle("Error during stage initialization")
                dlg.setText(error_message)
                dlg.exec()
                
                #Return immediately from this function
                return

            #Add a session message indicating the session is beginning
            message: SessionMessage = SessionMessage(f"Session started ({self._subject_name})")
            self._session_messages.append(message)
            self._update_session_messages()

            #Set the "session running" flag to True
            self._is_session_running = True

            #Set the text and text color on the start/stop button
            self._start_stop_button.setText("Stop")
            self._start_stop_button.setStyleSheet('QPushButton {color: red;}')

            #Disable the subject entry and the stage selection box
            self._subject_entry.setEnabled(False)
            self._subject_entry.setStyleSheet("QLineEdit {color: #808080; background-color: #F0F0F0;}")
            
            self._stage_selection_box.setEnabled(False)
            self._stage_selection_box.setStyleSheet("QComboBox {color: #808080; background-color: #F0F0F0;}")

            #Enable the plot selection combo boxes
            self._session_history_plot_selection_box.setEnabled(True)
            self._session_history_plot_selection_box.setStyleSheet("QComboBox {color: #000000; background-color: #FFFFFF;}")
            self._most_recent_trial_plot_selection_box.setEnabled(True)
            self._most_recent_trial_plot_selection_box.setStyleSheet("QComboBox {color: #000000; background-color: #FFFFFF;}")

            #Enable the pause and feed buttons
            self._pause_button.setEnabled(True)
            self._feed_button.setEnabled(True)
        else:
            #Disconnect from the signals of the selected stage
            self._selected_stage.signals.new_message.disconnect(self._on_message_received_from_stage)

            #Set the "session running" flag to False
            self._is_session_running = False

            #Finalize the stage and close the data file
            self._selected_stage.finalize()

            #Update she session message box
            message: SessionMessage = SessionMessage(f"Session stopped ({self._subject_name})")
            self._session_messages.append(message)
            self._update_session_messages()

            #Check if the session was paused at the time that the user
            #pressed the "stop" button
            if (self._is_session_paused):
                #If necessary, reset the "session paused" flag
                self._is_session_paused = False

                #Also make sure the pause button has the correct text
                self._pause_button.setText("Pause")

            #Set the text and text color on the start/stop button
            #Also disable the start/stop button (it will become enabled 
            #again after the user enters a new subject name for the next experiment)
            self._start_stop_button.setText("Start")
            self._start_stop_button.setEnabled(False)
            self._start_stop_button.setStyleSheet('QPushButton {color: #9D9D9D;}')

            #Disable the pause and feed buttons
            self._pause_button.setEnabled(False)
            self._feed_button.setEnabled(False)

            #Reset the subject name to be empty
            self._subject_entry.setText("")

            #Enable the subject entry and the stage selection box
            self._subject_entry.setEnabled(True)
            self._subject_entry.setStyleSheet("QLineEdit {color: #000000; background-color: #FFFFFF;}")

            self._stage_selection_box.setEnabled(True)
            self._stage_selection_box.setStyleSheet("QComboBox {color: #000000; background-color: #FFFFFF;}")

            #Disable the plot selection combo boxes
            self._session_history_plot_selection_box.setEnabled(False)
            self._session_history_plot_selection_box.setStyleSheet("QComboBox {color: #808080; background-color: #F0F0F0;}")
            self._most_recent_trial_plot_selection_box.setEnabled(False)
            self._most_recent_trial_plot_selection_box.setStyleSheet("QComboBox {color: #808080; background-color: #F0F0F0;}")
    
    def _on_pause_button_clicked (self) -> None:
        #Set the "paused" flag
        self._is_session_paused = not self._is_session_paused

        #Check if the session is now paused
        if (self._is_session_paused):
            #Change the pause button text to "resume"
            self._pause_button.setText("Resume")

            #The start/stop button will remain enabled, 
            #so the user can still stop the session if they want.
            #But let's make sure the feed button is disabled
            self._feed_button.setEnabled(False)
        else:
            #Change the pause button text to "pause"
            self._pause_button.setText("Pause")

            #Enable the feed button
            self._feed_button.setEnabled(True)

    def _on_message_received_from_stage (self, message: SessionMessage) -> None:
        self._session_messages.append(message)
        self._update_session_messages()

    def _on_user_command_entered (self) -> None:

        if (self._is_session_running) and (not (self._is_session_paused)):
            #Get the text that the user entered
            user_input: str = self._command_entry.text()

            #Clear the text in the UI
            self._command_entry.setText("")

            #Pass the text to the stage
            self._selected_stage.input(user_input)

        pass

    def _on_session_history_plot_selection_index_changed (self) -> None:
        if (self._is_session_running):
            current_index = self._session_history_plot_selection_box.currentIndex()
            self._selected_stage.session_plot_index = current_index

    def _on_most_recent_trial_plot_selection_index_changed (self) -> None:
        if (self._is_session_running):
            current_index = self._most_recent_trial_plot_selection_box.currentIndex()
            self._selected_stage.trial_plot_index = current_index

    #endregion

    #region Private methods

    def _update_session_messages (self) -> None:
        self._session_message_box.appendHtml(self._session_messages[-1].formatted_message_text)

        pass

    def _clear_session_messages (self) -> None:
        #Clear the session messages
        self._session_messages.clear()

        #Clear the UI edit box
        self._session_message_box.clear()

    #endregion

    #region Plot Methods

    def _initialize_live_emg_plot (self) -> None:
        '''
        Configures the Live EMG plot
        '''

        #Style the plot
        self._live_emg_graph_widget.setBackground('w')
        self._live_emg_graph_widget.setYRange(-250, 250, padding = 0)

        #Create the line object that will be used for updating the data
        pen = pg.mkPen(color = (0, 0, 255), width = 2)
        self._live_emg_x_data = list(range(0, len(self._emg_signal_data)))
        self._live_emg_line_object = self._live_emg_graph_widget.plot(self._live_emg_x_data, self._emg_signal_data, pen = pen)

    def _plot_live_emg(self) -> None:
        """
        Plots the current live EMG data.

        Parameters:
            figure (Figure): Matplotlib Figure object for the live EMG plot.
        """
        self._live_emg_line_object.setData(self._live_emg_x_data, self._emg_signal_data)
        
    #endregion
