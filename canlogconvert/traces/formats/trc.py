import pyparsing as pp
import pprint

# Load a CAN TRC file


# Currently only aims to support Version 2.1

# Column Order:
#   [N],O,T,[B],I,d,[R],l/L,D

# N: Message number, index of recorded message. Optional.
# This is the array index

# O: Time offset since start of the trace. Resolution: 1 microsecond.
# Milliseconds before the decimal separator, microseconds (3 digits) behind
# the decimal separator.

#  pp.ParserElement.setDefaultWhitespaceChars(" \t")

ControlComment = pp.Combine(pp.Literal(";") + pp.Literal("$"))
FileVersion = pp.Group(
    ControlComment
    + pp.Literal("FILEVERSION")
    + pp.Literal("=")
    + pp.Combine(pp.Word(pp.nums) + pp.Literal(".") + pp.Word(pp.nums))
    + pp.LineEnd()
)
StartTime = pp.Group(
    ControlComment
    + pp.Literal("STARTTIME")
    + pp.Literal("=")
    + pp.Combine(
        pp.ZeroOrMore(pp.Word(pp.nums))
        + pp.Literal(".")
        + pp.ZeroOrMore(pp.Word(pp.nums))
    )
    + pp.LineEnd()
)
Columns = pp.Group(
    ControlComment
    + pp.Literal("COLUMNS")
    + pp.Literal("=")
    + pp.Group(
        # Message Number
        pp.Optional(pp.Literal("N") + pp.Literal(","))
        # Time Offset (ms)
        + pp.Literal("O")
        + pp.Literal(",")
        # Type
        + pp.Literal("T")
        + pp.Literal(",")
        # Bus (1-16)
        # If Bus column is included, for events the Bus number can be specified as
        # '-' if the event is not associated with a specific bus
        + pp.Optional(pp.Literal("B") + pp.Literal(","))
        # CAN-ID (Hex)
        # 4 digits for 11-bit CAN-IDs (0000-07FF).
        # 8 digits for 29-bit CAN-IDs (00000000-1FFFFFFF).
        # Contains ‘-‘ for the message types EC, ER, ST, see ‘T’ column.
        + pp.Literal("I")
        + pp.Literal(",")
        # Direction.
        # Indicates whether the message was received ('Rx') or transmitted ('Tx').
        + pp.Literal("d")
        + pp.Literal(",")
        + pp.Optional(pp.Literal("R") + pp.Literal(","))
        + pp.oneOf("l L")
        + pp.Literal(",")
        + pp.Literal("D")
    )
    + pp.LineEnd()
)

LineComment = (
    pp.Literal(";")
    + pp.NotAny(pp.Or(FileVersion ^ StartTime ^ Columns))
    + pp.Regex(r".*")
    + pp.LineEnd()
)


Header = FileVersion + StartTime + Columns

Comment = StartTime  # ^ FileVersion ^ Columns)

# [N],O,T,[B],I,d,[R],l/L,D
BusNumber = pp.Or(
    pp.Literal("1")
    ^ pp.Literal("2")
    ^ pp.Literal("3")
    ^ pp.Literal("4")
    ^ pp.Literal("5")
    ^ pp.Literal("6")
    ^ pp.Literal("7")
    ^ pp.Literal("8")
    ^ pp.Literal("9")
    ^ pp.Literal("10")
    ^ pp.Literal("11")
    ^ pp.Literal("12")
    ^ pp.Literal("13")
    ^ pp.Literal("14")
    ^ pp.Literal("15")
    ^ pp.Literal("16")
    ^ pp.Literal("-")
)
ColumnDirection = pp.Or(pp.Literal("Rx") ^ pp.Literal("Tx"))
ColumnData = pp.Optional(pp.Word(pp.hexnums)) + pp.ZeroOrMore(
    pp.Literal(" ") + pp.Word(pp.hexnums)
)
#  ColumnCanId = pp.Literal()

MessageType = pp.Or(
    pp.Literal("DT")
    ^ pp.Literal("FD")
    ^ pp.Literal("FB")
    ^ pp.Literal("FE")
    ^ pp.Literal("BI")
    ^ pp.Literal("RR")
    ^ pp.Literal("ST")
    ^ pp.Literal("EC")
    ^ pp.Literal("ER")
)

MessageNumber = pp.Word(pp.nums)

TimeOffset = pp.Combine(pp.Word(pp.nums) + pp.Literal(".") + pp.Word(pp.nums))

CanID = pp.Combine(pp.OneOrMore(pp.Word(pp.hexnums)))

ColumnReserved = pp.Literal("-")
ColumnDLC = pp.Word(pp.nums)
ColumnData = pp.Combine(
    pp.Optional(pp.Word(pp.hexnums))
    + pp.ZeroOrMore(pp.Literal(" ") + pp.Word(pp.hexnums))
)

LineData = pp.Group(
    MessageNumber
    + TimeOffset
    + MessageType
    + BusNumber
    + CanID
    + ColumnDirection
    + ColumnReserved
    + ColumnDLC
    + ColumnData
    #  + pp.LineEnd()
)
TrcFileFormat = Header + pp.ZeroOrMore(pp.Or(LineComment ^ LineData))

# T: Type of message
class TraceMessageType:
    # CAN or J1939 data frame
    CAN_DATA_FRAME = "DT"
    # CAN FD data frame
    CAN_FD_FRAME = "FD"
    # CAN FD data frame with BRS bit set (Bit Rate Switch)
    CAN_FD_BRS_FRAME = "FB"
    # CAN FD data frame with ESI bit set (Error State Indicator)
    CAN_FD_ESI_FRAME = "FE"
    # CAN FD data frame with both BRS and ESI bits set
    CAN_FD_BRS_ESI_FRAME = "BI"
    # Remote Request Frame
    RTR_FRAME = "RR"
    # Hardware Status change
    HW_STATUS_CHANGE = "ST"
    # Error Counter change
    ERROR_COUNTER_CHANGE = "EC"
    # Error Frame
    ERROR_FRAME = "ER"
    # Event. User-defined text, begins directly after bus specifier.
    EVENT = "EV"


# B: Bus (1-16), optional. If Bus column is included, for events the Bus
# number can be specified as ‘-‘ if the event is not associated with a specific
# bus.

# I: CAN-ID (Hex)
# 4 digits for 11-bit CAN-IDs (0000-07FF).
# 8 digits for 29-bit CAN-IDs (00000000-1FFFFFFF).
# Contains ‘-‘ for the message types EC, ER, ST, see ‘T’ column

# d: Direction. Indicates whether the message was received (‘Rx’) or transmitted (‘Tx’).
class Direction:
    DIRECTION_TX = "Tx"
    DIRECTION_RX = "Rx"


# R: Reserved. Only used for J1939 protocol. Contains ‘-‘ for CAN busses. For
# J1939 protocol, contains destination address of a Transport Protocol PDU2
# Large Message. Optional for files that contain only CAN or CAN FD frames.

# l: Data Length (0-1785). This is the actual number of data bytes, not the
# Data Length Code (0..15). Optional. If omitted, the Data Length Code column
# (‘L’) must be included.

# L: Data Length Code (CAN: 0..8; CAN FD: 0..15; J1939: 0..1785).
# Optional. If omitted, the Data Length column (‘l’) must be included

# D: Data. 0-1785 data bytes in hexadecimal notation.
# For Data Frames (message types DT, FD, FB, FE, BI, see ‘T’ column): Data
# bytes of message, if Data Length is > 0.
# Empty for Remote Request frames (message type RR).
# For Hardware Status changes (message type ST): 4-byte status code in Motorola
# format.
# For Error Frames (message type ER): 5 bytes of Error Frame data, see Error
# Frames under Version 2.0.
# For Error Counter changes (message type EC): 2 bytes of Error Counter data.
# The first byte contains the RX Error counter, the second byte the TX Error
# counter.


"""

    +---------+-------------------+--------------------------+
    | Version | File header       | Used by                  |
    +=========+===================+==========================+
    | 1.0     | -                 | PCAN-Explorer 3.0        |
    |         |                   | PCAN-Trace 1.0           |
    +---------+-------------------+--------------------------+
    | 1.1     | ;$FILEVERSION=1.1 | PCAN-Explorer 3.0.2      |
    |         |                   | PCAN-Explorer 4          |
    |         |                   | PCAN-Trace 1.5           |
    |         |                   | PCAN-View 3              |
    +---------+-------------------+--------------------------+
    | 1.2     | ;$FILEVERSION=1.2 | PCAN-Explorer 5.0 Beta 1 |
    +---------+-------------------+--------------------------+
    | 1.3     | ;$FILEVERSION=1.3 | PCAN-Explorer 5          |
    +---------+-------------------+--------------------------+
    | 2.0     | ;$FILEVERSION=2.0 | PCAN-View 4              |
    +---------+-------------------+--------------------------+
    | 2.1     | ;$FILEVERSION=2.1 | PCAN-Explorer 6          |
    +---------+-------------------+--------------------------+

Currently we only support TRC
"""

FILE_HEADER_VERSION_1_1 = ";$FILEVERSION=1.1"
FILE_HEADER_VERSION_1_2 = ";$FILEVERSION=1.2"
FILE_HEADER_VERSION_1_3 = ";$FILEVERSION=1.3"
FILE_HEADER_VERSION_2_0 = ";$FILEVERSION=2.0"
FILE_HEADER_VERSION_2_1 = ";$FILEVERSION=2.1"


def _resolve_trc_version(lines):
    if len(lines):
        if lines[0] == FILE_HEADER_VERSION_1_1:
            return "1.1"
        elif lines[0] == FILE_HEADER_VERSION_1_2:
            return "1.2"
        elif lines[0] == FILE_HEADER_VERSION_1_3:
            return "1.3"
        elif lines[0] == FILE_HEADER_VERSION_2_0:
            return "2.0"
        elif lines[0] == FILE_HEADER_VERSION_2_1:
            return "2.1"

    # Otherwise we assume this is 1.0
    return "1.0"


def _parse_starttime(lines):
    # $STARTTIME keyword to store the absolute start time of the trace file
    #
    # Integral part = Number of days that have passed since 12/30/1899
    # Fractional Part = Fraction of a 24-hour day that has elapsed, resolution
    # is 1 millisecond.
    #
    # ;$STARTTIME=43474.7738065227
    # COMMA $ = NUMBER+ PERIOD NUMBER+
    return


def _parse_columns(lines):
    # ;$COLUMNS=N,O,T,B,I,d,R,L,D
    return


def load_string(string):
    lines = string.split("\n")
    if not _resolve_trc_version(lines) == "2.1":
        raise Error("We only support 2.1")
    pp = pprint.PrettyPrinter(indent=4)
    for val in TrcFileFormat.parseString(string):
        print(val)


"""
FILEVERSION_HEADER = COMMA + DOLLAR_SIGN + 'FILEVERSION' + EQUAL + FILEVERSION
FILEVERSION = NUMBER + '.' + NUMBER



COMMENT = COMMA + Not()
"""
#  r'\s+(\d+)\s+(\d+\.\d+)\s+(DT)\s+(\d+)\s+([\dA-F]+)\s+(Rx|Tx)\s+(.)+\s+(\d+)\s+(\d{2}+)'