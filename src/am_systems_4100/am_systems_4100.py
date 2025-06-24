import serial
import socket
from dataclasses import dataclass

from .am_systems_4100_comm_constants import CONSTANTS
from .am_systems_4100_comm_constants import VALUES

@dataclass
class AmSystems4100_ConnectionInfo:
    pin: int = 1204

@dataclass
class AmSystems4100_SerialConnectionInfo (AmSystems4100_ConnectionInfo):
    port_name: str = ""

@dataclass
class AmSystems4100_TcpConnectionInfo (AmSystems4100_ConnectionInfo):
    ip_address: str = ""
    port: int = 23

class TcpBuffer:

    def __init__(self, sock: socket.socket):
        self._sock = sock
        self.buffer = b''
        pass

    def read_until (self, delimiter: bytes) -> bytes:
        while delimiter not in self.buffer:
            data = self._sock.recv(1024)
            if not data:
                return None
            
            self.buffer += data
        
        line, sep, self.buffer = self.buffer.partition(delimiter)
        return line

'''
This class interfaces with the A-M Systems 4100 Instrumentation Amplifier.
'''
class AmSystems4100:

    #region Constructor

    def __init__(self, connection_info: AmSystems4100_ConnectionInfo):

        #Set the library id. We will always just use 1 here.
        self._lib_id: int = 1

        #Store the pin from the connection information
        self._am4100_pin: int = connection_info.pin

        if (isinstance(connection_info, AmSystems4100_SerialConnectionInfo)):
            #Initialize the connection with the A-M systems stimulator
            self._initialize_serial_connection(connection_info)
        elif (isinstance(connection_info, AmSystems4100_TcpConnectionInfo)):
            self._initialize_tcpip_connection(connection_info)

        pass

    #endregion

    #region Private methods for serial communication

    def _initialize_serial_connection (self, connection_info: AmSystems4100_SerialConnectionInfo) -> None:

        #Set private data members
        self._am4100_serial_com_port: str = connection_info.port_name
        
        try:
            self._serial_port = serial.Serial(self._am4100_serial_com_port, 115200, timeout=10)
            self._serial_port.bytesize = serial.EIGHTBITS
            self._serial_port.stopbits= serial.STOPBITS_ONE
            self._serial_port.parity = serial.PARITY_ODD
            self._serial_port.write_timeout = 10
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            self._serial_port = None

        pass

    def _clear_serial_buffers (self) -> None:
        if (self._serial_port is not None):
            self._serial_port.reset_input_buffer()
            self._serial_port.reset_output_buffer()

    def _serial_send_command_and_read_response (self, command: str) -> list[str]:

        result: list[str] = []

        self._clear_serial_buffers()

        if (self._serial_port is not None):
            try:
                #DEBUGGING OUTPUT
                #print(f"Command: {command}")
                #END OF DEBUGGING OUTPUT

                #Encode the command
                encoded_command: bytes = command.encode()

                #Send the command
                self._serial_port.write(encoded_command)

                #Read the response
                response: bytes = self._serial_port.read_until(b'*\r\n')

                #Decode the response
                decoded_response: str = response.decode().strip()

                #Split the result using "\r" and "\n" as delimiters
                result = decoded_response.split("\r\n")

                #DEBUGGING OUTPUT
                #print(f"Response received: ")
                #for i in range(0, len(result)):
                #    print(result[i])
                #print("")
                #END OF DEBUGGING OUTPUT

            except serial.SerialException as e:
                print(f"Error sending command or reading response: {e}")

        return result

    #endregion

    #region TcpIp communication

    def _initialize_tcpip_connection (self, connection_info: AmSystems4100_TcpConnectionInfo) -> None:

        #Create a socket object
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #Set the connection timeout to 10 seconds
        self._sock.settimeout(10)

        #Attempt to connect to the device
        try:
            self._sock.connect((connection_info.ip_address, connection_info.port))
            print("AM Systems 4100 connection successful")
        except socket.timeout:
            print("Connection time out to AM Systems 4100 stimulator")
            self._sock = None
            pass
        except socket.error as e:
            print(f"AM Systems 4100 connection error: {e}")
            self._sock = None
            pass

        #Create a buffer to hold the data received from the socket
        self._socket_buffer = TcpBuffer(self._sock)

        pass

    def _tcpip_send_command_and_read_response (self, command: str) -> list[str]:

        result: list[str] = []

        #self._clear_serial_buffers()

        if (self._sock is not None):
            try:
                #DEBUGGING OUTPUT
                print(f"Command: {command}")
                #END OF DEBUGGING OUTPUT

                #Encode the command
                encoded_command: bytes = command.encode()

                #Send the command
                self._sock.send(encoded_command)

                #Read the response
                response: bytes = self._socket_buffer.read_until(b'*')

                #Decode the response
                decoded_response: str = response.decode().strip()

                #Split the result using "\r" and "\n" as delimiters
                result = decoded_response.split("\r\n")

                #DEBUGGING OUTPUT
                print(f"Response received: ")
                for i in range(0, len(result)):
                    print(result[i])
                print("")
                #END OF DEBUGGING OUTPUT

            except serial.SerialException as e:
                print(f"Error sending command or reading response: {e}")

        return result

    #endregion

    #region Communication-type agnostic methods

    def _send_command_and_read_response (self, command: str) -> list[str]:

        if (hasattr(self, "_serial_port")):
            if (self._serial_port is not None):
                return self._serial_send_command_and_read_response(command)
        elif (hasattr(self, "_sock")):
            if (self._sock is not None):
                return self._tcpip_send_command_and_read_response(command)

        return []

    def _send_get_command (self, preliminary_command: str) -> list[str]:

        command: str = "get " + preliminary_command + "\r"
        
        return self._send_command_and_read_response(command)

    def _send_set_command (self, preliminary_command: str) -> list[str]:

        command: str = str(self._am4100_pin) + " set " + preliminary_command + "\r"

        return self._send_command_and_read_response(command)

    #endregion

    #region Public methods

    def get_firmware_revision (self) -> str:
        '''
        Returns the firmware revision
        '''

        command: str = "revision"
        result: list[str] = self._send_get_command(command)

        if (len(result) > 1):
            return result[1]

        return ""
    
    def get_status (self) -> str:
        '''
        Returns the current status
        '''
        
        command: str = "active"
        result: list[str] = self._send_get_command(command)

        if (len(result) > 1):
            return result[1]
        
        return ""
    
    def get_network (self) -> list[str]:
        '''
        Returns the IP address, IP mask, and IP gateway
        '''
        
        command: str = "network"
        result: list[str] = self._send_get_command(command)

        if (len(result) >= 4):
            return [result[1], result[2], result[3]]

        return []

    def get_menu (self, menu_number: int, item_number: int) -> int:
        '''
        Returns the instrument setting for the specified menu # and item #.
        Values are returned as signed 64-bit integers representing uV, uA, or microseconds.
        '''
        
        command: str = f"menu {menu_number} {item_number}"
        result: list[str] = self._send_get_command(command)

        if (len(result) > 1):
            return int(result[1])

        return 0    
    
    def get_condition (self) -> str:
        '''
        Returns two characters representing several instrument internal switches.

        First character bits:
            Bit 7 = 0
            Bit 6 = 1
            Bit 5 = 0
            Bit 4 = 1 if > 200 V
            Bit 3 = 1 if > 100 uA
            Bit 2 = 1 if FPGA is generating
            Bit 1 = 1 if FPGA is loaded, waiting/generating
            Bit 0 = 1 if enable button is depressed
        
        Second character bits:
            Bit 7 = 0
            Bit 6 = 1
            Bit 5 = 0
            Bit 4 = 0
            Bit 3 = 0
            Bit 2 = 1 if relay is open
            Bit 1 = 1 if the front panel is on free run
            Bit 0 = 1 if the front panel has been changed
        '''

        command: str = "condition"
        result: list[str] = self._send_get_command(command)

        if (len(result) > 1):
            return result[1]
        
        return ""
    
    def set_active (self, run: bool) -> None:
        '''
        Either starts or stops the generation of pulses
        '''
        
        parameter: str = "run"
        if (not run):
            parameter = "stop"
        command: str = f"active {parameter}"

        self._send_set_command(command)
    
    def set_network (self, ip_address: str, mask: str, gateway: str) -> None:
        '''
        Sets the IP address, mask, and gateway
        '''
        
        command: str = f"network {ip_address} {mask} {gateway}"
        self._send_set_command(command)

    def set_menu (self, menu_number: int, item_number: int, item_value: int) -> None:
        '''
        Sets the value of the item in the menu to the specified value.
        The value is a 64-bit signed integer in uV, uA, or microseconds.
        Microseconds have only positive values.
        '''

        command: str = f"menu {menu_number} {item_number} {item_value}"
        self._send_set_command(command)
    
    def set_trigger (self, trigger_type: str) -> None:
        '''
        Generates an output trigger.

        - "free-run" starts output without trigger
        - "none" cancels free-run and system waits for a hardware trigger
        - "one" generates a single trigger
        '''

        command: str = f"trigger {trigger_type}"
        self._send_set_command(command)
    
    def set_relay (self, open: bool) -> None:
        '''
        Opens or closes the relay on the output of the instrument
        '''

        relay_open: str = "open"
        if (not open):
            relay_open = "close"

        command: str = f"relay {relay_open}"
        self._send_set_command(command)

    #endregion

    #region Higher level public methods

    def set_train_delay (self, train_delay: int) -> None:
        '''
        Sets the duration from trigger input until the onset of the first pulse in the train.
        This is in units of microseconds. The train_delay value must be between 0 and 9,360,000,000.
        '''

        #Return immediately if the train_delay parameter is out of range
        if (train_delay < 0) or (train_delay > 9_360_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the train delay value
        self.set_menu(CONSTANTS.MENU.TRAIN, CONSTANTS.TRAIN.DELAY, train_delay)

        pass

    def set_train_duration (self, train_duration: int) -> None:
        '''
        The train duration is the duration of the pulse train, in units of microseconds.
        This epoch of time begins at the end of the train delay.
        The train_duration value must be between 2 and 9,360,000,000.
        '''

        #Return immediately if the train_duration parameter is out of range
        if (train_duration < 2) or (train_duration > 9_360_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the train duration parameter
        self.set_menu(CONSTANTS.MENU.TRAIN, CONSTANTS.TRAIN.DURATION, train_duration)

        pass

    def set_train_period (self, train_period: int) -> None:
        '''
        The train period is the interval between the onset of successive train durations.
        This is in units of microseconds. The train_period value must be between 2 and 9,360,000,000.
        '''

        #Return immediately if the train_period parameter is out of range
        if (train_period < 2) or (train_period > 9_360_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the train period parameter
        self.set_menu(CONSTANTS.MENU.TRAIN, CONSTANTS.TRAIN.PERIOD, train_period)

        pass

    def set_train_quantity (self, train_quantity: int) -> None:
        '''
        The train quantity is the number of trains delivered per trigger.
        Train quantity must be an integer between 1 and 100.
        '''

        #Return immediately if the train_quantity parameter is out of range
        if (train_quantity < 1) or (train_quantity > 100):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the train quantity parameter
        self.set_menu(CONSTANTS.MENU.TRAIN, CONSTANTS.TRAIN.QUANTITY, train_quantity)

        pass

    def set_auto (self, auto_type: int) -> None:
        '''
        Sets the "auto" parameter. The Model 4100 has two built-in algorithms to simplify
        programming for common protocols. The "auto" function can be set to none (0), count (1),
        or fill (2).

        The "count" setting can be summarized as "deliver the specified quantity of events". In this
        case, the user defines the events to be delivered, the event intervals, and the quantity of
        events, but does not specify the train duration. Instead, the Model 4100 will calculate the
        minimum train width required to completely deliver the requested number of events at the 
        requested interval when given a single trigger input.

        The "fill" setting can be summarized as "deliver events for a specified time duration". In
        this case, the user defines the events to be generated, the event intervals, and the train
        duration, but does not specify the total quantity of events.
        '''

        #Return immediately if the auto_type parameter is out of bounds
        if (auto_type < 0) or (auto_type > 2):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the auto parameter
        self.set_menu(CONSTANTS.MENU.GENERAL, CONSTANTS.GENERAL.AUTO, auto_type)

        pass
    
    def set_mode (self, mode: int) -> None:
        '''
        The mode must be between 0 and 5.

        The mode determines if the Model 4100 is producing voltage or current pulses
        using its internal circuitry, or acting as an analog isolator and scaling the
        user supplied signal to the SIGNAL IN BNC.

        The modes are:
            - Produce voltage pulses                    = 0
            - Produce current pulses                    = 1
            - External SIGNAL IN BNC 20V / V            = 2
            - External SIGNAL IN BNC 10 mA / V          = 3
            - External SIGNAL IN BNC 1 mA / V           = 4
            - External SIGNAL IN BNC 100 uA / V         = 5
        '''

        #Return immediately if the mode parameter is out of range
        if (mode < 0) or (mode > 5):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the mode
        self.set_menu(CONSTANTS.MENU.GENERAL, CONSTANTS.GENERAL.MODE, mode)

        pass

    def set_event_period (self, event_period: int) -> None:
        '''
        Sets the period of an event in units of microseconds.

        For example, if you want an event to happen at a frequency of 30 Hz (30 times per second), 
        then that event would have a period of 33,333 microseconds.

        Math: 1,000,000 microseconds / 30 = 33,333.33 microseconds

        The "event_period" parameter must be an integer from 2 to 9,360,000,000.
        '''

        #Return immediately if the event_period parameter is out of range
        if (event_period < 2) or (event_period > 9_360_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the parameter
        menu_number: int = CONSTANTS.MENU.EVENT + (self._lib_id - 1)
        self.set_menu(menu_number, CONSTANTS.EVENT.PERIOD, event_period)

        pass

    def set_event_quantity (self, event_quantity: int) -> None:
        '''
        Sets the number of events to occur in the train.
        
        The "event_quantity" parameter must be an integer from 0 to 99,999.
        '''

        #Return immediately if the event_quantity parameter is out of range
        if (event_quantity < 0) or (event_quantity > 99_999):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the parameter
        menu_number: int = CONSTANTS.MENU.EVENT + (self._lib_id - 1)
        self.set_menu(menu_number, CONSTANTS.EVENT.QUANTITY, event_quantity)

        pass

    def set_event_type (self, event_type: int) -> None:
        '''
        Sets the type of event / pulse. 
        The options are monophasic (0), biphasic (1), asymettric (2), or ramp (3).

        When an event is biphasic, The amplitude of both phases is determined by event_amplitude1.
        Likewise, the duration of both phases is determined by event_duration1.

        When an event is asymettric, the amplitude and duration of the 2nd phase are determined
        by event_amplitude2 and event_duration2.
        '''

        #Return immediately if the event_type parameter is out of bounds
        if (event_type < 0) or (event_type > 3):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the event type
        menu_number: int = CONSTANTS.MENU.EVENT + (self._lib_id - 1)
        self.set_menu(menu_number, CONSTANTS.EVENT.TYPE, event_type)

        pass

    def set_event_duration1 (self, event_duration: int) -> None:
        '''
        This sets the duration of:
            1. A monophasic pulse
            2. Both phases of a biphasic pulse
            3. The first phase of an asymettric pulse
        
        The event_duration parameter is in units of microseconds.
        It must be an integer from 1 to 9360000000.
        '''

        #Return immediately if the event_duration parameter is out of range
        if (event_duration < 1) or (event_duration > 9_360_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the event_duration1 parameter
        menu_number: int = CONSTANTS.MENU.EVENT + (self._lib_id - 1)
        self.set_menu(menu_number, CONSTANTS.EVENT.DUR_1, event_duration)

        pass

    def set_event_amplitude1 (self, event_amplitude: int) -> None:
        '''
        This sets the amplitude of:
            1. A monophasic pulse
            2. Both phases of a biphasic pulse
            3. The first phase of an asymmetric pulse
        
        The event_amplitude parameter must be an integer from 0 to 200000000.
        It is in units of uA (microamps).
        '''

        #Return immediately if the event_amplitude parameter is out of range
        if (event_amplitude < 0) or (event_amplitude > 200_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)        

        #Set the event_amplitude1 parameter
        menu_number: int = CONSTANTS.MENU.EVENT + (self._lib_id - 1)
        self.set_menu(menu_number, CONSTANTS.EVENT.AMP_1, event_amplitude)

        pass

    def set_event_duration2 (self, event_duration: int) -> None:
        '''
        This sets the duration of the second phase of an asymmetric pulse.
        The event_duration parameter is in units of microseconds.
        It must be an integer from 0 to 9360000000.
        '''

        #Return immediately if the event_duration parameter is out of range
        if (event_duration < 0) or (event_duration > 9_360_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the event_duration1 parameter
        menu_number: int = CONSTANTS.MENU.EVENT + (self._lib_id - 1)
        self.set_menu(menu_number, CONSTANTS.EVENT.DUR_2, event_duration)

        pass

    def set_event_amplitude2 (self, event_amplitude: int) -> None:

        '''
        This sets the amplitude of the second phase of an asymmetric pulse.
        The event_amplitude parameter must be an integer from 0 to 200000000.
        It is in units of uA (microamps).
        '''

        #Return immediately if the event_amplitude parameter is out of range
        if (event_amplitude < 0) or (event_amplitude > 200_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)        

        #Set the event_amplitude1 parameter
        menu_number: int = CONSTANTS.MENU.EVENT + (self._lib_id - 1)
        self.set_menu(menu_number, CONSTANTS.EVENT.AMP_2, event_amplitude)

        pass

    def set_event_duration3 (self, event_duration: int) -> None:
        '''
        This sets the interval between phases in a biphasic, asymmetric, or ramp event.
        The documentation does not refer to anything called "duration 3", but they do have a separate thing
        in the documentation called "interval" - and I think they are referring to the same thing.

        The event_duration parameter is in units of microseconds.
        It must be an integer from 0 to 9360000000.
        '''

        #Return immediately if the event_duration parameter is out of range
        if (event_duration < 0) or (event_duration > 9_360_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the event_duration1 parameter
        menu_number: int = CONSTANTS.MENU.EVENT + (self._lib_id - 1)
        self.set_menu(menu_number, CONSTANTS.EVENT.DUR_3, event_duration)

        pass

    def set_event_delay (self, event_delay: int) -> None:
        '''
        Event delay is the duration from the end of the train delay until the onset of the first event.
        There is only ONE single event delay per train, regardless of the number of events requested per train.

        The event delay must be an integer from 0 to 9360000000. It is in units of microseconds.
        '''

        #Return immediately if the event_delay parameter is out of range
        if (event_delay < 0) or (event_delay > 9_360_000_000):
            return
        
        #Stop any stimulation train that is currently active
        self.set_active(False)

        #Set the event delay
        menu_number: int = CONSTANTS.MENU.EVENT + (self._lib_id - 1)
        self.set_menu(menu_number, CONSTANTS.EVENT.DELAY, event_delay)

        pass

    #endregion

    #region Very higher level public methods

    def set_txbdc_standard_vns_parameters (self) -> None:
        '''
        This function sets the stimulation parameters on the Model 4100 to be
        TxBDC's standard VNS parameters.

        Specifically, the parameters are set to be:

            - Event delay: 0 uS (this means there is no delay from the beginning of the train epoch for events to begin)
            - Event type: biphasic
            - Event frequency: 30 Hz
                - We set the "event period" to be 33,333 uS
            - Event duration 1: 100 uS (this means both phases of a biphasic pulse will be 100 uS in duration)
            - Event amplitude 1: 0.8 mA (both phases of a biphasic pulse will be 0.8 mA in amplitude)
            - Event duration 2: Set to 0, not used for biphasic pulses
            - Event amplitude 2: Set to 0, not used for biphasic pulses
            - Event duration 3: Set to 0, indicating 0 uS between the two phases of a biphasic pulse
            - Train delay: 0 uS
            - Train quantity: 1 (so 1 stimulation train per trigger pulse)
            - Train duration: 500 ms
        '''

        #Calculate the event period
        event_frequency: float = 30.0
        event_period: int = round(1_000_000 / event_frequency)

        #Stop any active stimulation
        self.set_active(False)

        #Tell the unit to produce "current" pulses (not "voltage" pulses).
        self.set_mode(1)

        #Tell the stimulator unit that we will not provide a specific number
        #of pulses for it to generate. Rather, it needs to "fill" the train
        #duration with pulses at the appropriate intervals until the duration
        #has completed.
        self.set_auto(2)

        #Tell the stimulator unit that there will be 0 delay between the trigger
        #and the onset of the stimulation train.
        self.set_train_delay(0)

        #Tell the stimulator unit that we will produce 1 stimulation train.
        self.set_train_quantity(1)

        #Tell the stimulator unit that the stimulation train will have a duration
        #of 500 milliseconds.
        self.set_train_duration(500_000)

        #Tell the stimulator unit that there will be 0 delay between the onset
        #of the stimulation train and the first event within the train.
        self.set_event_delay(0)

        #Tell the stimulator unit that we want to use biphasic pulses.
        self.set_event_type(1)

        #Tell the stimulator unit the appropriate spacing between pulses. In this case,
        #we want to deliver pulses at a frequency of 30 Hz, so the period is 33,333 uS.
        self.set_event_period(event_period)

        #Tell the stimulator unit that each phase of the biphasic pulse will be 100 uS
        #in duration.
        self.set_event_duration1(100)

        #Tell the stimulator unit that each phase of the biphasic pulse will be 0.8 mA
        #in amplitude.
        self.set_event_amplitude1(800)

        #Biphasic pulses do not use "duration2" and "amplitude2", so we will set them
        #to a value of 0.
        self.set_event_duration2(0)
        self.set_event_amplitude2(0)

        #Tell the stimulator unit that there is 0 uS interval between the two phases
        #of the biphasic pulse.
        self.set_event_duration3(0)

        pass

    def trigger_single (self) -> None:
        self.set_trigger("one")
        pass

    def trigger_free_run (self) -> None:
        self.set_trigger("free-run")
        pass

    #endregion