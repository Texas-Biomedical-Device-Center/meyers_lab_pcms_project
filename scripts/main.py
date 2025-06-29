import sys
from PySide6 import QtWidgets
from PySide6.QtWidgets import QMessageBox
from pcms_txbdc.view.main_window import MainWindow
#from pcms_txbdc.model.stimjim import discover_ports
from ...am_systems_4100 import AmSystems4100_ConnectionInfo, discover_ports
from pcms_txbdc.model.application_configuration import ApplicationConfiguration
from serial.tools.list_ports_common import ListPortInfo
import serial

AM_4100_SERIAL_INFO = "VID:PID=0403:6001"   # This is for FTDI
REQUIRE_AM_4100: bool = False

def discover_ports(pattern=AM_4100_SERIAL_INFO):
    ports = list(serial.tools.list_ports.grep(pattern))
    return ports

def main () -> None:
    #Create the QT application
    app = QtWidgets.QApplication(sys.argv)

    #Discover serial ports that match the StimJim hardware
    possible_ports: list[ListPortInfo] = discover_ports()

    #Check to see if any ports matching the StimJim were discovered
    if REQUIRE_AM_4100 and (len(possible_ports) == 0):
        #If not, display an error message to the user
        #and then return immediately.
        dlg: QMessageBox = QMessageBox()
        dlg.setWindowTitle("Error! A-M Systems 4100 Stimulator not detected!")
        dlg.setText("The application was unable to detect a stimulator connected to the computer. The application cannot proceed.")
        dlg.exec()

        return

    #Connect to the AM Systems Model 4100
    if (len(possible_ports) > 0):
        ApplicationConfiguration.connect_to_am_systems_4100(possible_ports[0].device)

    #Connect to the StimJim
    # for port in possible_ports:
    #     ApplicationConfiguration.connect_to_stimjim(port)

    #Instantiate the MainWindow object
    window = MainWindow()

    #Display the main window
    window.show()

    #Turn control over to QT's main loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
