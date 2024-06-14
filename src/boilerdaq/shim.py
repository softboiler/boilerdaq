"""Shim that wraps some methods from UL for use in Python in Linux.

MIT License

Copyright (c) 2018 Measurement Computing

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# pyright: basic

from ctypes import CDLL, POINTER, byref, c_float, c_int, create_string_buffer
from ctypes.util import find_library
from enum import IntFlag
from sys import platform

if platform.startswith("darwin"):
    lib_file_name = "libuldaq.dylib"
else:
    lib_file_name = "libuldaq.so"

lib_file_path = find_library("uldaq")
if lib_file_path is None:
    lib_file_path = lib_file_name
lib = CDLL(lib_file_path)
lib.ulTIn.argtypes = [c_int, c_int, c_int, POINTER(c_float), c_int]


def _check_err(errcode):
    if errcode:
        raise ULError(errcode)


class ULError(Exception):  # noqa: D101
    def __init__(self, errorcode):
        super().__init__()
        self.errorcode = errorcode
        self.message = get_err_msg(errorcode)

    def __str__(self):
        return "Error " + str(self.errorcode) + ": " + self.message


_ERRSTRLEN = 256


def get_err_msg(error_code):
    """Return the error message associated with an error code.

    It is usually unnecessary to use
    this method externally, since ULError errors raised by this module assign the value to the
    message property. Some functions do return an error code in cases where it is used as a
    warning. Call this function to convert the returned error code to a descriptive error message.

    Parameters
    ----------
    error_code
        The error code that is returned by some functions in this library.

    Returns
    -------
    string
        The error message associated with the given error_code
    """
    msg = create_string_buffer(_ERRSTRLEN)
    _check_err(lib.ulGetErrMsg(error_code, msg))
    return msg.value.decode("utf-8")


class TInOptions(IntFlag):  # noqa: D101
    FILTER = 0x0000  # Filter thermocouple inputs
    NOFILTER = 0x0400  # Disable filtering for thermocouple

    WAITFORNEWDATA = 0x2000  # Wait for new data to become available


def t_in(board_num, channel, scale, options=TInOptions.FILTER):
    """Read an analog input channel.

    Linearize it according to the selected temperature sensor type, if required, and
    return the temperature in units determined by the scale parameter.

    Parameters
    ----------
    board_num : int
        The number associated with the board when it was installed with InstaCal or created
        with :func:`.create_daq_device`.
    channel : int
        Input channel to read.
    scale : TempScale
        Specifies the temperature scale that the input will be converted to
    options : TInOptions, optional
        Flags that control various options. Refer to the constants in the "options parameter values"
        section below.

    Returns
    -------
    float
        The temperature value


    .. table:: **options parameter values**

        ==============  ===========================================================================
        FILTER          When selected, a smoothing function is applied to temperature readings,
                        very much like the electrical smoothing inherent in all hand held
                        temperature sensor instruments. This is the default. When selected, 10
                        samples are read from the specified channel and averaged. The average is
                        the reading returned. Averaging removes normally distributed signal line
                        noise.
        --------------  ---------------------------------------------------------------------------
        NOFILTER        If you use the NOFILTER option then the readings will not be smoothed and
                        you will see a scattering of readings around a mean.
        --------------  ---------------------------------------------------------------------------
        WAITFORNEWDATA  Waits for new data to become available.
        ==============  ===========================================================================



    Notes
    -----
    **Scale options**

    - Specify the TempScale.NOSCALE to the scale parameter to retrieve raw data from the device.
      When TempScale.NOSCALE is specified, calibrated data is returned, although a cold junction
      compensation (CJC) correction factor is not applied to the returned values.

    - Specify the :const:`~pyulmcculwms.TempScale.VOLTS` option to read the voltage input of a
      thermocouple.

    Refer to board-specific information in the Universal Library User's Guide to determine if your
    hardware supports these options.
    """
    temp_value = c_float()
    _check_err(lib.ulTIn(board_num, channel, scale, byref(temp_value), options))
    return temp_value.value


def v_in(board_num, channel, ul_range, options=0):
    """Read an A/D input channel, return a voltage value.

    If the specified A/D board has programmable gain, then this function sets the gain
    to the specified range.

    Parameters
    ----------
    board_num : int
        The number associated with the board when it was installed with InstaCal or
        created with :func:`.create_daq_device`.
    channel : int
        A/D channel number. The maximum allowable channel depends on which type of A/D
        board is being used. For boards with both single-ended and differential inputs,
        the maximum allowable channel number also depends on how the board is
        configured.
    ul_range : ULRange
        A/D range code. If the board has a programmable gain, it will be set according
        to this parameter value. Keep in mind that some A/D boards have a programmable
        gain feature, and others set the gain via switches on the board. In either case,
        the range that the board is configured for must be passed to this function.
        Refer to board specific information for a list of the supported A/D ranges of
        each board.
    options : int, optional
        Reserved for future use

    Returns
    -------
    float
        The value in volts of the A/D sample
    """
    data_value = c_float()
    _check_err(lib.ulVIn(board_num, channel, ul_range, byref(data_value), options))
    return data_value.value
