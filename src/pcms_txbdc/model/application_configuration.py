from serial.tools.list_ports_common import ListPortInfo
import serial
import time

from am_systems_4100.am_systems_4100 import AmSystems4100
from am_systems_4100.am_systems_4100 import AmSystems4100_SerialConnectionInfo, AmSystems4100_TcpConnectionInfo
#from .stimjim import StimJim, PulseTrain, PulseStage, StimJimOutputModes, STIMJIM_SERIAL_BAUDRATE

class ApplicationConfiguration:

    #The name of the application
    appname: str = "PCMS"

    #The author/organization of the application
    appauthor: str = "TxBDC"

    # AM Systems 4100 stimulator object
    stimulator: list[AmSystems4100] = []

    #region Methods

    @staticmethod
    def connect_to_am_systems_4100 (port: ListPortInfo) -> None:
        # Create serial connection information object
        # connection_info: AmSystems4100_SerialConnectionInfo = AmSystems4100_SerialConnectionInfo(
        #   port.device     # COM port number for windows (i.e. COM10)
        # )

        # Create TCP connection information object
        connection_info: AmSystems4100_TcpConnectionInfo = AmSystems4100_TcpConnectionInfo(
            1204,           # pin number
            "10.133.71.4"   # IP address
        )

        #Connect to the stimulator
        new_am4100 = AmSystems4100(connection_info)
        ApplicationConfiguration.stimulator.append(new_am4100)

    @staticmethod
    def disconnect_from_am_systems_4100 () -> None:
        if (ApplicationConfiguration.stimulator is not None):
            try:
                for stim in ApplicationConfiguration.stimulator:
                    ApplicationConfiguration.stimulator[stim]._sock.close()
                ApplicationConfiguration.stimulator = None
            except:
                pass

    @staticmethod
    def TEST_set_monophasic_stimulus_pulse_parameters (index: int, amplitude_ma: float) -> None:
        #   Current = decided by the caller of the function
        #   Frequency = N/A
        #   Pulse phase width = 500 us
        #   Biphasic pulse
        #   Train duration = 1000 us
        #   Total pulses = 1

        if index < len(ApplicationConfiguration.stimulator):
            stim: AmSystems4100 = ApplicationConfiguration.stimulator[index]

            #Stop any active stimulation
            stim.set_active(False)

            #Tell the unit to produce "current" pulses (not "voltage" pulses).
            stim.set_mode(1)

            #Tell the stimulator unit that we will provide a specific number
            #of pulses for it to generate
            stim.set_auto(1)

            # Tell the stimulator unit that the period of 1 stimulation train will be 500_500 uS
            # in duration
            stim.set_event_period(500_500)

            #Tell the stimulator unit that there will be 0 delay between the trigger
            #and the onset of the stimulation train.
            stim.set_train_delay(0)

            #Tell the stimulator unit that we will produce 1 stimulation train.
            stim.set_train_quantity(1)

            #Tell the stimulator unit that there will be 0 delay between the onset
            #of the stimulation train and the first event within the train.
            stim.set_event_delay(0)

            #Tell the stimulator unit that we want to use biphasic pulses.
            stim.set_event_type(0)

            #Tell the stimulator unit that we will deliver exactly 1 pulse.
            stim.set_event_quantity(1)

            #Tell the stimulator unit that each phase of the biphasic pulse will be 500 uS
            #in duration.
            stim.set_event_duration1(500_000)

            #Tell the stimulator unit that each phase of the biphasic pulse will be 0.8 mA
            #in amplitude.
            stim.set_event_amplitude1(amplitude_ma)

            #Biphasic pulses do not use "duration2" and "amplitude2", so we will set them
            #to a value of 0.
            stim.set_event_duration2(0)
            stim.set_event_amplitude2(0)

        else:
            print("index out of range")

        pass

    @staticmethod
    def set_biphasic_stimulus_pulse_parameters (index: int, amplitude_ma: float) -> None:
        #   Current = decided by the caller of the function
        #   Frequency = N/A
        #   Pulse phase width = 500 us
        #   Biphasic pulse
        #   Train duration = 1000 us
        #   Total pulses = 1

        if index < len(ApplicationConfiguration.stimulator):
            stim: AmSystems4100 = ApplicationConfiguration.stimulator[index]

            #Stop any active stimulation
            stim.set_active(False)

            #Tell the unit to produce "current" pulses (not "voltage" pulses).
            stim.set_mode(1)

            #Tell the stimulator unit that we will provide a specific number
            #of pulses for it to generate
            stim.set_auto(1)

            #Tell the stimulator unit that there will be 0 delay between the trigger
            #and the onset of the stimulation train.
            stim.set_train_delay(0)

            #Tell the stimulator unit that we will produce 1 stimulation train.
            stim.set_train_quantity(1)

            #Tell the stimulator unit that there will be 0 delay between the onset
            #of the stimulation train and the first event within the train.
            stim.set_event_delay(0)

            #Tell the stimulator unit that we want to use biphasic pulses.
            stim.set_event_type(1)

            #Tell the stimulator unit that we will deliver exactly 1 pulse.
            stim.set_event_quantity(1)

            #Tell the stimulator unit that each phase of the biphasic pulse will be 500 uS
            #in duration.
            stim.set_event_duration1(500)

            #Tell the stimulator unit that each phase of the biphasic pulse will be 0.8 mA
            #in amplitude.
            stim.set_event_amplitude1(amplitude_ma)

            #Biphasic pulses do not use "duration2" and "amplitude2", so we will set them
            #to a value of 0.
            stim.set_event_duration2(0)
            stim.set_event_amplitude2(0)

            #Tell the stimulator unit that there is 0 uS interval between the two phases
            #of the biphasic pulse.
            stim.set_event_duration3(0)

        else:
            print("index out of range")

        pass

    @staticmethod
    def set_standard_vns_stimulation_parameters () -> None:
        #Standard VNS parameters:
        #   Current = 0.8 mA (800 uA)
        #   Frequency = 30 Hz
        #   Pulse phase width = 100 us
        #   Biphasic pulse
        #   Train duration = 500 ms (500000 microseconds)
        #   Total pulses = 15
        #   Pulses are delivered every 33.333 ms (or 33333 microseconds)

        if (ApplicationConfiguration.stimulator is not None):
            ApplicationConfiguration.stimulator.set_txbdc_standard_vns_parameters()

    #endregion