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
    QMessageBox,
    QSpacerItem
)

from PySide6.QtGui import QFont
from PySide6.QtCore import QThreadPool
from PySide6 import QtCore
from PySide6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
import pandas as pd
import os
from datetime import datetime
from datetime import timedelta
import time

from typing import Tuple

from ..model.open_ephys_streamer import OpenEphysStreamer
from ..model.background_worker import BackgroundWorker
from ..model.stages.stage import Stage
from ..model.stages.salinebath_demodata_stage import SalineBathDemoDataStage
from ..model.stages.pcms_stages import Stage0aFWaveLatency, Stage0bMEPLatency, PCMSConditioningStage #, SalineBathDemoDataStage, 

# from ..model.stages.emg_characterization_stage import EmgCharacterizationStage
# from ..model.stages.mh_recruitment_curve_stage import MhRecruitmentCurveStage
from ..model.session_message import SessionMessage
from ..model.application_configuration import ApplicationConfiguration

import serial

class MainWindow(QMainWindow):
    """
    Main application window for PCMS Conditioning with input fields for experimental variables
    and plots to visualize trial and live EMG data.
    """

    #region Constructor

    def __init__(self) -> None:
        super().__init__()

        # List to store message text entries
        self._msg_text_list = []  
        
        # Initialize a variable to hold EMG signal data for plotting
        self._emg_signal_data_max_length = 50000
        self._emg_signal_data = np.zeros(self._emg_signal_data_max_length)

        # Initialize a flag to track whether a session is currently running
        self._is_session_running: bool = False
        self._is_session_paused: bool = False

        # STAGES -  FROM '..MODEL/STAGE/PSCMS_Stage' File
        # Initialize a list of stages
        self._stages: list[Stage] = []

        salinebath_demodata_stage: SalineBathDemoDataStage = SalineBathDemoDataStage()
        self._stages.append(salinebath_demodata_stage)

        stage_0a = Stage0aFWaveLatency()
        self._stages.append(stage_0a)

        stage_0b = Stage0bMEPLatency()
        self._stages.append(stage_0b)

        pcms_stage_1 = PCMSConditioningStage(
            name="Stage 1: PCMS Conditioning",
            description="15 min PCMS, 5s interval, Stim #0 and #1",
            interval_sec=5,
            duration_min=15,
            stim_indices=[0, 1, 2]
        )
        self._stages.append(pcms_stage_1)

        pcms_stage_2 = PCMSConditioningStage(
            name="Stage 2: VNS-PCMS Conditioning",
            description="15 min PCMS with vagus, 5s interval, Stim #0 and #1",
            interval_sec=5,
            duration_min=15,
            stim_indices=[0, 1, 2]
        )
        self._stages.append(pcms_stage_2)





        # Initialize the "selected stage"
        self._selected_stage: Stage = self._stages[0]

        # Initialize a variable to hold the subject name
        self._subject_name: str = ""

        # Initialize a set of messages that will be displayed in the session message box
        self._session_messages: list[SessionMessage] = []

        # Set up window title and size
        self.setWindowTitle("PCMS Conditioning")
        self.resize(900, 600)  # Increased the width of the window

        #Create some fonts that will be used for the ui elements
        self._regular_font: QFont = QFont("Arial", 12)
        self._bold_font: QFont = QFont("Arial", 12, QFont.Bold)
        self._large_bold_font: QFont = QFont("Arial", 20, QFont.Bold)

        # Main layout container
        self._layout: QGridLayout = QGridLayout()
        self._layout.setRowStretch(0, 0)
        self._layout.setRowStretch(1, 2)    # Middle section - increased
        self._layout.setRowStretch(2, 2)    # Bottom section - decreased
        self._layout.setRowStretch(3, 0)
        # Format: setRowStretch(row_number, stretch_factor)

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
        # for s in self._stages:
        #     s.set_session_and_trial_widgets(self._session_history_plot_widget, self._previous_trial_plot_widget)

        # Initialize the threadpool and the background worker
        self.threadpool = QThreadPool()
        self.background_worker = BackgroundWorker()
        self.background_worker.signals.data_received_signal.connect(self._on_data_received)
        self.threadpool.start(self.background_worker)

    #endregion
            
    #region Methods for creating the user interface
    def _create_top_section(self) -> None:
        """
        Creates the top section of the window with subject entry, stage dropdown, and channel dropdown
        """
        # Create main top layout as a grid with 3 columns
        top_grid = QGridLayout()
        top_grid.setColumnStretch(0, 1)     # Subject entry
        top_grid.setColumnStretch(1, 1)     # Spacer
        top_grid.setColumnStretch(2, 1)     # Stage selection
        top_grid.setColumnStretch(3, 1)     # Spacer
        top_grid.setColumnStretch(4, 1)     # Channel selection
        
        # First row left - Subject entry
        subject_layout = QHBoxLayout()
        subject_label = QLabel("Subject: ")
        subject_label.setFont(self._bold_font)

        # Subject text entry
        self._subject_entry = QLineEdit("")
        self._subject_entry.setFont(self._regular_font)
        self._subject_entry.setStyleSheet("QLineEdit {color: #000000; background-color: #FFFFFF;}")
        self._subject_entry.editingFinished.connect(self._on_subject_name_edited)
        self._msg_text_list.append(self._subject_entry) #store the text entry for later access.

        #Add subject entry elements to layout
        subject_layout.addWidget(subject_label)
        subject_layout.addWidget(self._subject_entry)
        subject_layout.addStretch()
        top_grid.addLayout(subject_layout, 0, 0)
        
        #First row center - Stage dropdown
        stage_layout = QHBoxLayout()
        stage_label = QLabel("Stage: ")
        stage_label.setFont(self._bold_font)

        #Stage selection box
        self._stage_selection_box = QComboBox()
        self._stage_selection_box.setFont(self._regular_font)
        self._stage_selection_box.setStyleSheet("QComboBox {color: #000000; background-color: #FFFFFF;}")
        self._stage_selection_box.currentIndexChanged.connect(self._on_stage_selection_changed)

        #Populate the stage selection box
        stage_strings: list[str] = []
        for s in self._stages:
            stage_str: str = f"({s.stage_name}) {s.stage_description}"
            stage_strings.append(stage_str)
        self._stage_selection_box.addItems(stage_strings)

        #Add elements to layout
        stage_layout.addStretch()
        stage_layout.addWidget(stage_label)
        stage_layout.addWidget(self._stage_selection_box)
        stage_layout.addStretch()
        top_grid.addLayout(stage_layout, 0, 2)
        
        # First row right - EMG channel dropdown
        channel_layout = QHBoxLayout()
        channel_label = QLabel("EMG Channel: ")
        channel_label.setFont(self._bold_font)

        # Channel selection box
        self._channel_selection_box = QComboBox()
        self._channel_selection_box.setFont(self._regular_font)
        self._channel_selection_box.setStyleSheet("QComboBox {color: #000000; background-color: #FFFFFF;}")
        self._channel_selection_box.currentIndexChanged.connect(self._on_channel_selection_changed)

        # Populate the stage selection box
        channel_list: list[int] = list(range(1, 17))
        self._channel_selection_box.addItems([str(c) for c in channel_list])

        # Add elements to layout
        channel_layout.addStretch()
        channel_layout.addWidget(channel_label)
        channel_layout.addWidget(self._channel_selection_box)
        top_grid.addLayout(channel_layout, 0, 4)

        # Add top grid to main layout
        self._layout.addLayout(top_grid, 0, 0)

    def _create_middle_section(self) -> None:
        """
        Creates the middle section with two EMG data plots: one for peri-stimulus EMG data
        and one for displaying the EMG values of the last 50 trials.
        """
        middle_grid = QGridLayout()
        middle_grid.setRowStretch(0, 0)
        middle_grid.setRowStretch(1, 1)
        middle_grid.setColumnStretch(0, 1)
        middle_grid.setColumnStretch(1, 1)

        peri_stim_label = QLabel("Peri-Stimulus EMG signal")
        peri_stim_label.setFont(self._bold_font)
        peri_stim_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        live_emg_label = QLabel("Live EMG signal")
        live_emg_label.setFont(self._bold_font)
        live_emg_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        #This plot widget will show the session history
        self._peri_stim_plot_widget = pg.PlotWidget()
        self._peri_stim_plot_widget.setBackground('w')

        #This plot will show the live EMG data
        self._live_emg_graph_widget = pg.PlotWidget()
        self._initialize_live_emg_plot()

        # Add both plots to the middle layout
        # middle_grid.addWidget(history_plot_label, 0, 0)
        middle_grid.addWidget(peri_stim_label, 0, 0)
        # middle_grid.addWidget(self._most_recent_trial_plot_selection_box, 0, 1)
        middle_grid.addWidget(live_emg_label, 0, 1)

        middle_grid.addWidget(self._peri_stim_plot_widget, 1, 0)
        # middle_grid.addWidget(self._previous_trial_plot_widget, 1, 1)
        middle_grid.addWidget(self._live_emg_graph_widget, 1, 1)

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
        bottom_layout.setColumnStretch(2, 0)
        bottom_layout.setColumnStretch(3, 0)
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

        # Create 2 buttons: brain stim, nerve stim.
        self._brain_stim_button = QPushButton("Brain Stim")
        self._brain_stim_button.setFont(self._regular_font)
        self._brain_stim_button.setFixedWidth(100)
        self._brain_stim_button.setMaximumHeight(150)
        self._brain_stim_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self._brain_stim_button.setStyleSheet('QPushButton {color: red;}')
        self._brain_stim_button.setEnabled(True)
        self._brain_stim_button.clicked.connect(self._on_single_stim_button_clicked)

        self._nerve_stim_button = QPushButton("Nerve Stim")
        self._nerve_stim_button.setFont(self._regular_font)
        self._nerve_stim_button.setFixedWidth(100)
        self._nerve_stim_button.setMaximumHeight(150)
        self._nerve_stim_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self._nerve_stim_button.setStyleSheet('QPushButton {color: red;}')
        self._nerve_stim_button.setEnabled(True)
        self._nerve_stim_button.clicked.connect(self._on_single_stim_button_clicked)

        # Create a grid layout to hold the buttons
        stim_button_layout = QGridLayout()
        stim_button_layout.setRowStretch(0, 1)
        stim_button_layout.setRowStretch(1, 1)
        
        # Add the buttons to the button layout
        stim_button_layout.addWidget(self._brain_stim_button, 0, 0)
        stim_button_layout.addWidget(self._nerve_stim_button, 1, 0)

        # Create 4 buttons: up and down buttons for brain/nerve stim
        self._brain_stim_up_button = QPushButton("▲")
        self._brain_stim_up_button.setFixedSize(30, 30)
        self._brain_stim_up_button.setEnabled(True)
        self._brain_stim_up_button.clicked.connect(self._on_stim_amplitude_up_down_button_clicked)
        self._brain_stim_down_button = QPushButton("▼")
        self._brain_stim_down_button.setFixedSize(30, 30)
        self._brain_stim_down_button.setEnabled(True)
        self._brain_stim_down_button.clicked.connect(self._on_stim_amplitude_up_down_button_clicked)
        
        self._nerve_stim_up_button = QPushButton("▲")
        self._nerve_stim_up_button.setFixedSize(30, 30)
        self._nerve_stim_up_button.setEnabled(True)
        self._nerve_stim_up_button.clicked.connect(self._on_stim_amplitude_up_down_button_clicked)
        self._nerve_stim_down_button = QPushButton("▼")
        self._nerve_stim_down_button.setFixedSize(30, 30)
        self._nerve_stim_down_button.setEnabled(True)
        self._nerve_stim_down_button.clicked.connect(self._on_stim_amplitude_up_down_button_clicked)

        # Create default values of stimulation amplitudes
        Stage.STIM1_AMPLITUDE = 5.0    # µA
        Stage.STIM2_AMPLITUDE = 3.0    # µA
        self._stim_step_size = 0.1      # µA step per click

        # Create 2 text boxes: brain/nerve stim amplitude
        self._brain_stim_amplitude_textbox = QLineEdit()
        self._brain_stim_amplitude_textbox.setFixedSize(30, 30)
        self._brain_stim_amplitude_textbox.setText(f"{Stage.STIM1_AMPLITUDE:.1f}")
        self._brain_stim_amplitude_textbox.editingFinished.connect(self._on_stim_amplitude_changed)
        self._brain_stim_button.setAutoDefault(False)
        
        self._nerve_stim_amplitude_textbox = QLineEdit()
        self._nerve_stim_amplitude_textbox.setFixedSize(30, 30)
        self._nerve_stim_amplitude_textbox.setText(f"{Stage.STIM2_AMPLITUDE:.1f}")
        self._nerve_stim_amplitude_textbox.editingFinished.connect(self._on_stim_amplitude_changed)
        self._nerve_stim_button.setAutoDefault(False)

        # Create 2 box layouts: brain/nerve stim amplitude textbox and µA label
        brain_amplitude_layout = QHBoxLayout()
        brain_amplitude_layout.addWidget(self._brain_stim_amplitude_textbox, alignment=Qt.AlignCenter)
        brain_amplitude_label = QLabel("mA")        # label for stim amplitude unit
        brain_amplitude_label.setAlignment(Qt.AlignVCenter)
        brain_amplitude_layout.addWidget(brain_amplitude_label)
        
        nerve_amplitude_layout = QHBoxLayout()
        nerve_amplitude_layout.addWidget(self._nerve_stim_amplitude_textbox, alignment=Qt.AlignCenter)
        nerve_amplitude_label = QLabel("mA")        # label for stim amplitude unit
        nerve_amplitude_label.setAlignment(Qt.AlignVCenter)
        nerve_amplitude_layout.addWidget(nerve_amplitude_label)

        # Create box layout to hold brain stim combo of up/amplitude/down
        brain_combo_layout = QVBoxLayout()
        brain_combo_layout.addStretch(1)
        brain_combo_layout.addWidget(self._brain_stim_up_button)
        brain_combo_layout.addLayout(brain_amplitude_layout)
        brain_combo_layout.addWidget(self._brain_stim_down_button)
        brain_combo_layout.addStretch(1)
        
        # Create box layout to hold nerve stim combo of up/amplitude/down
        nerve_combo_layout = QVBoxLayout()
        nerve_combo_layout.addStretch(1)
        nerve_combo_layout.addWidget(self._nerve_stim_up_button)
        nerve_combo_layout.addLayout(nerve_amplitude_layout)
        nerve_combo_layout.addWidget(self._nerve_stim_down_button)
        nerve_combo_layout.addStretch(1)

        # Create a grid layout to hold up/down buttons
        up_down_button_layout = QGridLayout()
        up_down_button_layout.setRowStretch(0, 1)  # brain stim layout
        up_down_button_layout.setRowStretch(1, 1)  # nerve stim layout

        # Add the combo box layout to the up/down button layout
        up_down_button_layout.addLayout(brain_combo_layout, 0, 0)
        up_down_button_layout.addLayout(nerve_combo_layout, 1, 0)

        #Create 3 buttons: start/stop, pause, and feed
        self._start_stop_button = QPushButton("Start")
        self._start_stop_button.setFont(self._large_bold_font)
        self._start_stop_button.setFixedWidth(200)
        self._start_stop_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self._start_stop_button.setEnabled(False)
        self._start_stop_button.setStyleSheet('QPushButton {color: #9D9D9D;}')
        self._start_stop_button.clicked.connect(self._on_start_stop_button_clicked)

        self._pause_button = QPushButton("Pause")
        self._pause_button.setFont(self._large_bold_font)
        self._pause_button.setFixedWidth(200)
        self._pause_button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self._pause_button.setEnabled(False)
        #self._pause_button.clicked.connect(self._on_pause_button_clicked)

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

        # Add the brain/nerve stim layout to the bottom layout
        bottom_layout.addLayout(stim_button_layout, 0, 1, 2, 1)

        # Add the up/down button layout to the bottom layout
        bottom_layout.addLayout(up_down_button_layout, 0, 2, 2, 1)

        #Add the button layout to the bottom layout
        bottom_layout.addLayout(button_layout, 0, 3, 2, 1)

        #Add the bottom layout to the primary grid layout
        self._layout.addLayout(bottom_layout, 2, 0)


        # button for stages: stims controls are created
        self._connect_stim_button = QPushButton("Connect Stim")
        self._connect_stim_button.setFont(self._regular_font)
        self._connect_stim_button.setStyleSheet('QPushButton {color: blue;}')
        self._connect_stim_button.setFixedWidth(150)
        self._connect_stim_button.clicked.connect(self._on_connect_stimulator_clicked)
        bottom_layout.addWidget(self._connect_stim_button, 0, 4)  # adjust position if needed


        pass

    #endregion

    #region Overrides

    def _send_callback(self) -> None:
        """
        Handler for send button clicks from any of the input rows.
        """
        # Get the sender (the button or text entry that triggered the callback)
        sender = self.sender()
        
        # Find which text entry was used
        text_entry = None
        stim_number = None
        if isinstance(sender, QLineEdit):
            text_entry = sender
            # Find which Stim Jim this is
            if text_entry in self._msg_text_list:
                stim_number = self._msg_text_list.index(text_entry) + 1
        elif isinstance(sender, QPushButton):
            # Get the text entry associated with this button's row
            # (it will be the previous widget in the layout)
            layout = sender.parent().layout()
            for i in range(layout.count()):
                if isinstance(layout.itemAt(i).widget(), QLineEdit):
                    text_entry = layout.itemAt(i).widget()
                    stim_number = self._msg_text_list.index(i) + 1
                    break

        if text_entry and text_entry.text().strip():
            # Add to session messages
            message = SessionMessage(f"Message to stim jim{stim_number}: {text_entry.text()}")
            self._session_messages.append(message)
            self._update_session_messages()
            
            # Clear the text entry
            text_entry.clear()

    def closeEvent(self, event):
        '''
        This method is called when the user attempts to close the application window.
        This method handles gracefully shutting the application down.
        '''

        #Disconnect from the data received signal
        self.background_worker.signals.data_received_signal.disconnect(self._on_data_received)

        #Shut down the background thread
        self.background_worker.cancel()

        #Close the AM 4100 stimulator serial/tcp connection if it exists
        ApplicationConfiguration.disconnect_from_am_systems_4100()

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
        if (len(self._subject_entry.text()) > 0):#and (self._selected_stage is not None):
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
        # if (self._selected_stage is not None):
        #     items: list[str] = self._selected_stage.get_session_plot_options()

        #     self._session_history_plot_selection_box.clear()
        #     for i in items:
        #         self._session_history_plot_selection_box.addItem(i)

        #     items: list[str] = self._selected_stage.get_trial_plot_options()

        #     self._most_recent_trial_plot_selection_box.clear()
        #     for i in items:
        #         self._most_recent_trial_plot_selection_box.addItem(i)

        # Check to see if the start/stop button should be enabled
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

    def _on_channel_selection_changed (self) -> None:
        '''
        This function is executed anytime the user selects a channel
        in the EMG channel selection box.
        '''

        #Set the selected stage
        current_stage_index = self._channel_selection_box.currentIndex()
        if (current_stage_index >= 0):
            OpenEphysStreamer.CHANNEL_SHOWN = current_stage_index
        else:
            OpenEphysStreamer.CHANNEL_SHOWN = 0

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
    
    def _on_single_stim_button_clicked(self) -> None:
        """
        Handles clicks for Brain/Nerve Stim buttons.
        Outputs which stimulator (row) was activated.
        """
        sender = self.sender()
        label = None
        amplitude = None
        stim_number = None

        # Determine if it's brain or nerve based on which button was clicked
        if sender == self._brain_stim_button:
            label = "Brain"
            amplitude = Stage.STIM1_AMPLITUDE
            stim_number = 0
        elif sender == self._nerve_stim_button:
            label = "Nerve"
            amplitude = Stage.STIM2_AMPLITUDE
            stim_number = 1
        else:
            # Unknown sender
            return
            
        # Output an error message if no AM 4100 stimulator is found. Else, send command to send stimulus
        if not (0 <= stim_number < len(ApplicationConfiguration.stimulator)) or ApplicationConfiguration.stimulator[stim_number] is None:
            # Format and send the message
            message = SessionMessage(f"AM 4100 stimulator #{stim_number} not connected!")
            self._session_messages.append(message)
            self._update_session_messages()

        else:
            # Set stimulator parameters
            ApplicationConfiguration.set_biphasic_stimulus_pulse_parameters(stim_number, amplitude)
            stim = ApplicationConfiguration.stimulator[stim_number]
            
            time.sleep(0.1)     # wait for AM 4100 to load the parameters

            stim.set_active(True)
            stim.trigger_single()

            # Format and send the message
            message = SessionMessage(f"{label} AM 4100 #{stim_number} activated")
            self._session_messages.append(message)
            self._update_session_messages()

    def _on_stim_amplitude_up_down_button_clicked (self) -> None:
        sender = self.sender()

        # Change value based on button clicked
        if sender == self._brain_stim_up_button:
            # Increase brain stim amplitude by 0.1
            Stage.STIM1_AMPLITUDE = min(Stage.STIM1_AMPLITUDE + self._stim_step_size, 6.0)
            self._brain_stim_amplitude_textbox.setText(f"{Stage.STIM1_AMPLITUDE:.1f}")
        elif sender == self._brain_stim_down_button:
            # Decrease brain stim amplitude by 0.1
            Stage.STIM1_AMPLITUDE = max(0.0, Stage.STIM1_AMPLITUDE - self._stim_step_size)
            self._brain_stim_amplitude_textbox.setText(f"{Stage.STIM1_AMPLITUDE:.1f}")
        elif sender == self._nerve_stim_up_button:
            # Increase value by 0.1
            Stage.STIM2_AMPLITUDE = min(Stage.STIM2_AMPLITUDE + self._stim_step_size, 6.0)
            self._nerve_stim_amplitude_textbox.setText(f"{Stage.STIM2_AMPLITUDE:.1f}")
        elif sender == self._nerve_stim_down_button:
            # Increase value by 0.1
            Stage.STIM2_AMPLITUDE = max(0.0, Stage.STIM2_AMPLITUDE - self._stim_step_size)
            self._nerve_stim_amplitude_textbox.setText(f"{Stage.STIM2_AMPLITUDE:.1f}")
        else:
            # Unknown sender
            return

    def _on_stim_amplitude_changed(self) -> None:
        # Error handler for when non-numeric is imputted in textbox.
        brain_text = self._brain_stim_amplitude_textbox.text()
        nerve_text = self._nerve_stim_amplitude_textbox.text()

        try:
            Stage.STIM1_AMPLITUDE = float(brain_text)
        except ValueError:
            Stage.STIM1_AMPLITUDE = 5.0
            self._brain_stim_amplitude_textbox.setText(f"{Stage.STIM1_AMPLITUDE:.1f}")
            self._session_messages.append(SessionMessage("Invalid brain stim input! Reset to 5.0 mA."))
            self._update_session_messages() 

        try:
            Stage.STIM2_AMPLITUDE = float(nerve_text)
        except ValueError:
            Stage.STIM2_AMPLITUDE = 3.0
            self._nerve_stim_amplitude_textbox.setText(f"{Stage.STIM2_AMPLITUDE:.1f}")
            self._session_messages.append(SessionMessage("Invalid nerve stim input! Reset to 3.0 mA."))
            self._update_session_messages()

        # Set default values for the stim
        stim_info = [
            {
                "label": "brain",
                "value": Stage.STIM1_AMPLITUDE,
                "default": 5.0,
                "textbox": self._brain_stim_amplitude_textbox,
                "set_func": lambda v: setattr(self, "_brain_stim_value", v)
            },
            {
                "label": "nerve",
                "value": Stage.STIM2_AMPLITUDE,
                "default": 3.0,
                "textbox": self._nerve_stim_amplitude_textbox,
                "set_func": lambda v: setattr(self, "_nerve_stim_value", v)
            }
        ]

        for stim in stim_info:
            # Reject negative values according to the above default values
            if stim["value"] < 0:
                stim["set_func"](stim["default"])
                stim["textbox"].setText(f"{stim['default']:.1f}")

                message = SessionMessage(f"Negative {stim['label']} stim input! Reset to {stim['default']:.1f} mA.")
                self._session_messages.append(message)
                self._update_session_messages()

            # Reject values higher than 6.0 mA
            elif stim["value"] > 6.0:
                stim["set_func"](stim["default"])
                stim["textbox"].setText(f"{stim['default']:.1f}")

                message = SessionMessage(f"{stim['label']} stim input above limit! Reset to {stim['default']:.1f} mA.")
                self._session_messages.append(message)
                self._update_session_messages()

    def _on_start_stop_button_clicked (self) -> None:
        if (not self._is_session_running):
            #Clear the list of messages
            self._clear_session_messages()

            #Subscribe to signals from the selected stage
            self._selected_stage.signals.new_message.connect(self._on_message_received_from_stage)
            self._selected_stage.signals.session_complete.connect(self._on_stage_session_complete)

            #Initialize the selected stage
            init_result: tuple[bool, str] = self._selected_stage.initialize(self._subject_name)

            #Check to see if the stage can proceed
            if (not init_result[0]):
                #Disconnect from the signals of the selected stage
                self._selected_stage.signals.new_message.disconnect(self._on_message_received_from_stage)
                self._selected_stage.signals.session_complete.disconnect(self._on_stage_session_complete)

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

            # #Enable the plot selection combo boxes
            # self._session_history_plot_selection_box.setEnabled(True)
            # self._session_history_plot_selection_box.setStyleSheet("QComboBox {color: #000000; background-color: #FFFFFF;}")
            # self._most_recent_trial_plot_selection_box.setEnabled(True)
            # self._most_recent_trial_plot_selection_box.setStyleSheet("QComboBox {color: #000000; background-color: #FFFFFF;}")

            #Enable the pause and feed buttons
            self._pause_button.setEnabled(True)
            self._feed_button.setEnabled(True)
        else:
            #Disconnect from the signals of the selected stage
            self._selected_stage.signals.new_message.disconnect(self._on_message_received_from_stage)
            self._selected_stage.signals.session_complete.disconnect(self._on_stage_session_complete)

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
            # self._session_history_plot_selection_box.setEnabled(False)
            # self._session_history_plot_selection_box.setStyleSheet("QComboBox {color: #808080; background-color: #F0F0F0;}")
            # self._most_recent_trial_plot_selection_box.setEnabled(False)
            # self._most_recent_trial_plot_selection_box.setStyleSheet("QComboBox {color: #808080; background-color: #F0F0F0;}")
    
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

    def _on_stage_session_complete (self) -> None:
        # Called when session_complete signal is emit
        if (self._is_session_running):
            self._on_start_stop_button_clicked()

    def _on_user_command_entered (self) -> None:
        if (self._is_session_running) and (not (self._is_session_paused)):
            #Get the text that the user entered
            user_input: str = self._command_entry.text()

            #Clear the text in the UI
            self._command_entry.setText("")

            # Add the user's command to the session messages with special formatting
            message: SessionMessage = SessionMessage(f">> User Command: {user_input}")
            self._session_messages.append(message)
            self._update_session_messages()

            #Pass the text to the stage
            self._selected_stage.input(user_input)

    # def _on_session_history_plot_selection_index_changed (self) -> None:
    #     if (self._is_session_running):
    #         current_index = self._session_history_plot_selection_box.currentIndex()
    #         self._selected_stage.session_plot_index = current_index

    # def _on_most_recent_trial_plot_selection_index_changed (self) -> None:
    #     if (self._is_session_running):
    #         current_index = self._most_recent_trial_plot_selection_box.currentIndex()
    #         self._selected_stage.trial_plot_index = current_index

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
        



    def _on_connect_stimulator_clicked(self) -> None:
        try:
            # tries connecting to the AM Systems 4100 stimulators
            ApplicationConfiguration.connect_to_am_systems_4100(None)  # None means auto-detect
            # Success message
            self._session_messages.append(SessionMessage("SUCESS - Connected to AM Systems 4100 stimulator(s)."))
            # optionally enable stim buttons after connection
            self._brain_stim_button.setEnabled(True)
            self._nerve_stim_button.setEnabled(True)
            
        except Exception as e:
            # failure message
            self._session_messages.append(SessionMessage(f"Error - Connection failed: {str(e)}"))
            # disable stimjims buttons if connection fails
            self._brain_stim_button.setEnabled(False)
            self._nerve_stim_button.setEnabled(False)
            
        self._update_session_messages()


    #endregion