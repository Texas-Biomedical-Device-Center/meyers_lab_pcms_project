from typing import BinaryIO
from datetime import datetime
from datetime import timedelta
import struct

class FileIO_Helpers:

    type_dictionary = {
        'char': 'c',
        'int': 'i',
        'int32': 'i',
        'int8': 'b',
        'unsigned int': 'I',
        'uint8': 'B',
        'float': 'f',
        'float64': 'd',
        'double': 'd'
    }

    length_dictionary = {
        'char': 2,
        'int': 4,
        'int32': 4,
        'int8': 1,
        'unsigned int': 4,
        'uint8': 1,
        'float': 4,
        'float64': 8,
        'double': 8
    }     

    @staticmethod
    def write(opened_file: BinaryIO, desired_type: str, data) -> None:
        bytes_object: bytes = struct.pack(FileIO_Helpers.type_dictionary[desired_type], data)
        opened_file.write(bytes_object)
    
    @staticmethod
    def write_string (opened_file: BinaryIO, str_to_write: str) -> None:
        #Write the string's length
        FileIO_Helpers.write(opened_file, "int32", len(str_to_write))
        
        #Write the string's data
        bytes_object: bytes = str_to_write.encode("utf-8")
        opened_file.write(bytes_object)
    
    @staticmethod
    def write_datetime (opened_file: BinaryIO, dt: datetime) -> None:
        dt_float: float = FileIO_Helpers.convert_python_datetime_to_matlab_datenum(dt)
        FileIO_Helpers.write(opened_file, "float64", dt_float)

    @staticmethod
    def read(opened_file: BinaryIO, desired_type: str):
        """Reads a set number of bytes as the caller's desired type from an opened file.

        Arguments:
        opened_file -- A file handle to an opened file that is being read into memory.
        desired_type -- A string indicating what to read in from the opened file.

        desired_type can be any of the following strings:

        char -- Reads 2 bytes and interprets as a character
        int - Reads 4 bytes and interprets as an int
        int32 - Reads 4 bytes and interprets as an int
        int8 - Reads 1 byte and interprets as an int
        unsigned int - Reads 4 bytes and interprets as an unsigned int
        uint8 - Reads 1 byte and interprets as an unsigned int
        float - Reads 4 bytes and interprets as a floating point value
        float64 - Reads 8 bytes and interprets as a double-precision floating point value
        double - Reads 8 bytes and interprets as a double-precision floating point value
        """
               
        unpacked = struct.unpack(FileIO_Helpers.type_dictionary[desired_type], opened_file.read(FileIO_Helpers.length_dictionary[desired_type]))
        return unpacked[0]
    
    @staticmethod
    def read_string(opened_file: BinaryIO) -> str:

        #Read the string's length
        N: int = FileIO_Helpers.read(opened_file, "int32")

        #Read the string's content
        return opened_file.read(N).decode("utf-8")
    
    @staticmethod
    def read_datetime (opened_file: BinaryIO) -> datetime:
        dt_float: float = FileIO_Helpers.read(opened_file, "float64")
        return FileIO_Helpers.convert_matlab_datenum_to_python_datetime(dt_float)
    
    @staticmethod
    def convert_python_datetime_to_matlab_datenum (dt: datetime) -> float:
        """This function converts a Python datetime to a Matlab datenum format."""

        mdn = dt + timedelta(days = 366)
        frac_seconds = (dt-datetime(dt.year,dt.month,dt.day,0,0,0)).seconds / (24.0 * 60.0 * 60.0)
        frac_microseconds = dt.microsecond / (24.0 * 60.0 * 60.0 * 1000000.0)
        return mdn.toordinal() + frac_seconds + frac_microseconds        

    @staticmethod
    def convert_matlab_datenum_to_python_datetime(datenum: float) -> datetime:
        """
        Convert Matlab datenum into Python datetime.
        :param datenum: Date in datenum format
        :return:        Datetime object corresponding to datenum.
        """

        days = datenum % 1
        return datetime.fromordinal(int(datenum)) \
               + timedelta(days=days) \
               - timedelta(days=366)