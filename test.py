# from serial.tools.list_ports_common import ListPortInfo
# import serial
# import sys
# from PySide6.QtWidgets import QApplication, QWidget, QMessageBox
# import serial.tools.list_ports

# # Constants for StimJim device
# STIMJIM_SERIAL_BAUDRATE = 115200
# STIMJIM_SERIAL_INFO = "VID:PID=16C0:0483"  # This should be the VID:PID of your StimJim device

# # Global variable for StimJim serial connection
# stimjim_serial: serial.Serial = None

# def connect_to_stimjim(port: ListPortInfo) -> None:
#     """Connect to the StimJim via the serial port and display connection info."""
#     #stimjim_serial = "" # Use the global variable to store the serial connection
#     stimjim_serial = serial.Serial(port.device, baudrate=STIMJIM_SERIAL_BAUDRATE, timeout=1)
#     print(f"Successfully connected to StimJim on {port.device}")
#     print(f"stimjim_serial: {stimjim_serial}")

# def discover_ports(pattern=STIMJIM_SERIAL_INFO):
#     """Discover serial ports that match the pattern (for StimJim)."""
#     ports = list(serial.tools.list_ports.grep(pattern))
#     return ports

# def main() -> None:
#     """Main function to handle connection and display information."""
#     # Create the QT application
#     app = QApplication(sys.argv)

#     # Discover serial ports that match the StimJim hardware
#     possible_ports: list[ListPortInfo] = discover_ports()

#     # Check to see if any ports matching the StimJim were discovered
#     if len(possible_ports) == 0:
#         # If no matching device is found, display an error message and return
#         dlg = QMessageBox()
#         dlg.setWindowTitle("Error!")
#         dlg.setText("StimJim not detected. The application cannot proceed.")
#         dlg.exec()
#         return

#     # Connect to the first matching StimJim device
#     connect_to_stimjim(possible_ports[0])

#     # Show a message box with the connection info
#     dlg = QMessageBox()
#     dlg.setWindowTitle("Connected!")
#     dlg.setText(f"Successfully connected to StimJim on {possible_ports[0].device}")
#     dlg.exec()

#     # Turn control over to QT's main loop
#     #sys.exit(app.exec())

# if __name__ == "__main__":
#     main()


# # import serial
# # import time

# # # Define serial port (adjust the port according to your system, e.g., COM9 on Windows or /dev/ttyUSB0 on Linux)
# # ser = serial.Serial('COM9', baudrate=9600, timeout=1)  # Replace with your correct port

# # # Function to send command to Arduino
# # def send_command(serial, command):
# #     serial.write((command + '\n').encode())
# #     print(f"Sent command: {command}")

# # # Main program
# # if __name__ == "__main__":
# #     # Send the first command to Arduino
# #     send_command(ser, "S0,1,0,33333,50000000;800,5000,100;-800,5000,100")

# #     # Wait for a short period before sending the next command
# #     time.sleep(1)  # You can adjust the delay as needed

# #     # Send the second command to Arduino
# #     send_command(ser, "T0")
    
# #     # Optionally, you can loop to continuously send commands or trigger other actions
# #     # For example, to continuously send commands every 5 seconds:
# #     while True:
# #         send_command(ser, "T0")  # Send "T0" to Arduino
# #         time.sleep(5)  # Wait 5 seconds before sending the next command


# # #https://github.com/picotech/picosdk-python-wrappers






# from PySide6.QtWidgets import QWidget, QGridLayout, QLineEdit, QLabel, QPushButton, QHBoxLayout, QVBoxLayout
# from PySide6.QtCore import Qt
# from PySide6.QtGui import QFont

# class MyWindow(QWidget):
#     def __init__(self):
#         super().__init__()

#         # Initialize fonts
#         self._bold_font = QFont("Arial", 12, QFont.Bold)
#         self._regular_font = QFont("Arial", 10)

#         # Create the main layout (using a vertical layout)
#         self._layout = QVBoxLayout()

#         # Create the grid layout
#         grid = QGridLayout()
#         grid.setColumnStretch(0, 1)
#         grid.setColumnStretch(1, 1)

#         # Create a sub-grid on the left side for the subject and stage
#         left_grid = QGridLayout()
#         grid.addLayout(left_grid, 0, 0)

#         # Subject label
#         subject_label = QLabel("Subject: ")
#         subject_label.setFont(self._bold_font)
#         left_grid.addWidget(subject_label, 0, 0)

#         # Subject text entry
#         self._subject_entry = QLineEdit("")
#         self._subject_entry.setFont(self._regular_font)
#         self._subject_entry.setFixedWidth(150)
#         self._subject_entry.setStyleSheet("QLineEdit {color: #000000; background-color: #FFFFFF;}")
#         self._subject_entry.editingFinished.connect(self._on_subject_name_edited)
#         left_grid.addWidget(self._subject_entry, 0, 1)

#         # Add the grid layout to the main layout
#         self._layout.addLayout(grid)

#         # Create the main horizontal layout for the top section (stim jim)
#         top_layout = QHBoxLayout()
#         top_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # Left align the layout

#         # Stim Jim label
#         stim_label = QLabel("Message to Stim Jim: ")
#         stim_label.setFont(self._bold_font)
#         top_layout.addWidget(stim_label)

#         # Stim Jim text entry
#         self._msg_text = QLineEdit("")
#         self._msg_text.setFont(self._regular_font)
#         self._msg_text.setStyleSheet("QLineEdit {color: #000000; background-color: #FFFFFF;}")
#         top_layout.addWidget(self._msg_text)
#         self._msg_text.returnPressed.connect(self._on_send_button_clicked)

#         # Add Send button
#         send_button = QPushButton("Send")
#         send_button.setFont(self._regular_font)
#         send_button.clicked.connect(self._on_send_button_clicked)
#         top_layout.addWidget(send_button)

#         # Add top layout to the main layout
#         self._layout.addLayout(top_layout)

#         # Command entry
#         self._command_entry = QLineEdit("")
#         self._command_entry.setFont(self._regular_font)
#         self._command_entry.setPlaceholderText("Enter a command...")
#         self._command_entry.setStyleSheet("QLineEdit {color: #000000; background-color: #FFFFFF;}")
#         self._command_entry.returnPressed.connect(self._on_user_command_entered)
#         self._layout.addWidget(self._command_entry)

#         # Set the main layout for the window
#         self.setLayout(self._layout)

#     def _on_subject_name_edited(self):
#         print(f"Subject name edited: {self._subject_entry.text()}")

#     def _on_send_button_clicked(self):
#         print(f"Send button clicked with message: {self._msg_text.text()}")

#     def _on_user_command_entered(self):
#         print(f"Command entered: {self._command_entry.text()}")



# from PySide6.QtWidgets import (QWidget, QLabel, QHBoxLayout,
#                                    QVBoxLayout, QApplication)
    
# class MyWidget(QWidget):
#     def __init__(self):
#         super().__init__()

#         # Create a label with some text
#         self.label = QLabel("This is some text")

#         # Create a horizontal layout
#         hbox = QHBoxLayout()
#         hbox.addWidget(self.label)

#         # Set the layout for the widget
#         self.setLayout(hbox)

# if __name__ == '__main__':
#     app = QApplication([])
#     widget = MyWidget()
#     widget.show()
#     app.exec()



from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGridLayout,
    QVBoxLayout,
)
from PySide6.QtGui import QFont

class LayoutGenerator:
    def __init__(self, parent_layout, bold_font, regular_font, send_callback):
        """
        Initializes the LayoutGenerator.

        Args:
            parent_layout (QVBoxLayout): The main layout to which the generated layouts will be added.
            bold_font (QFont): The bold font to be used for labels.
            regular_font (QFont): The regular font to be used for text entries and buttons.
            send_callback (callable): The callback function to be executed when the send button is clicked or Enter is pressed.
        """
        self._parent_layout = parent_layout
        self._bold_font = bold_font
        self._regular_font = regular_font
        self._send_callback = send_callback
        self._msg_text = None

    def create_stim_jim_layout(self, row_index):
        """
        Creates the layout for the Stim Jim message row.

        Args:
            row_index (int): The row index in the grid layout where the Stim Jim layout will be added.
        """
        stim_layout = QHBoxLayout()

        # Stim jim label
        stim_label = QLabel("Msg to Stim Jim: ")
        stim_label.setFont(self._bold_font)
        stim_layout.addWidget(stim_label)

        # stim jim text entry
        self._msg_text = QLineEdit("")
        self._msg_text.setFont(self._regular_font)
        self._msg_text.setStyleSheet("QLineEdit {color: #000000; background-color: #FFFFFF;}")
        self._msg_text.returnPressed.connect(self._send_callback)
        stim_layout.addWidget(self._msg_text)

        # Add send button
        send_button = QPushButton("Send")
        send_button.setFont(self._regular_font)
        send_button.clicked.connect(self._send_callback)
        stim_layout.addWidget(send_button)

        return stim_layout

    def add_layout_to_grid(self, layout, grid_layout, row_index, column_index):
        """
        Adds a layout to a grid layout at the specified row and column.

        Args:
            layout (QLayout): The layout to be added.
            grid_layout (QGridLayout): The grid layout to which the layout will be added.
            row_index (int): The row index.
            column_index (int): The column index.
        """
        grid_layout.addLayout(layout, row_index, column_index)

    def create_and_add_stim_jim_row(self, top_grid, row_index):
        """
        Creates the Stim Jim layout and adds it to the grid.

        Args:
            top_grid (QGridLayout): The grid layout to which the Stim Jim row will be added.
            row_index (int): The row index for the Stim Jim row.
        """
        stim_layout = self.create_stim_jim_layout(row_index)
        self.add_layout_to_grid(stim_layout, top_grid, row_index, 0)
        stim_layout.addStretch() #push to the left

    def add_top_grid_to_parent(self, top_grid, parent_layout_row, parent_layout_column):
        """
        Adds the top grid layout to the parent layout.

        Args:
            top_grid (QGridLayout): The top grid layout to be added.
            parent_layout_row (int): The row index in the parent layout.
            parent_layout_column (int): The column index in the parent layout.
        """
        self._parent_layout.addLayout(top_grid, parent_layout_row, parent_layout_column)

    def get_message_text_lineedit(self):
        """
        Returns the QLineEdit object for the message text.
        """
        return self._msg_text

# Example usage (assuming you have self._layout, self._bold_font, self._regular_font, and self._on_send_button_clicked defined):

# Instantiate generator
# layout_generator = LayoutGenerator(self._layout, self._bold_font, self._regular_font, self._on_send_button_clicked)

# Create top grid layout
# top_grid = QGridLayout()

# Create and add the stim jim row
# layout_generator.create_and_add_stim_jim_row(top_grid, 1)

# Add the top grid to the main layout
# layout_generator.add_top_grid_to_parent(top_grid, 0, 0)