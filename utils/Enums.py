'''
### Enums Module

This module defines enumerations used throughout the project to classify and interpret
constants found in Ocarina of Time and Majora's Mask instrument banks and SEQ64-compatible XML.

Classes:
    `XMLTags`:
        An enumeration of XML element tags used for SEQ6-compatible bank serialization.
        These are used to identify and organize sections during XML parsing.

    `AudioSampleCodec`:
        Enumerates known audio sample encoding formats used by Ocarina of Time and Majora's Mask.

    `AudioStorageMedium`:
        Enumerates known storage mediums used by Ocarina of Time and Majora's Mask.

Functionality:
    - Provides strongly typed constants for use in parsing, validation, and serialization logic.
    - Improves readbility and reduces the likelihood of errors from magic numbers or strings.

Dependencies:
    `enum`:
        Used for defining enumeration types.

Intended Usage:
    This module should be imported wherever constant classification or tag identification
    is needed during XML parsing, binary parsing, or binary conversion.
'''

from enum import *


class XMLTags(Enum):
    ABINDEXENTRY = 'abindexentry'
    ABHEADER = 'abheader'
    ABBANK = 'abbank'
    ABDRUMLIST = 'abdrumlist'
    ABSFXLIST = 'absfxlist'
    INSTRUMENTS = 'instruments'
    DRUMS = 'drums'
    ENVELOPES = 'envelopes'
    SAMPLES = 'samples'
    ALADPCMLOOPS = 'aladpcmloops'
    ALADPCMBOOKS = 'aladpcmbooks'


class AudioSampleCodec(IntEnum):
    ADPCM = 0
    S8 = 1
    S16_INMEM = 2
    SMALL_ADPCM = 3
    REVERB = 4
    S16 = 5


class AudioStorageMedium(IntEnum):
    RAM = 0
    UNK = 1
    CART = 2
    DISK_DRIVE = 3
    RAM_UNLOADDED = 5


class CacheLoadType(IntEnum):
    PERMANENT = 0
    PERSISTENT = 1
    TEMPORARY = 2
    EITHER = 3
    EITHER_NOSYNC = 4


class SampleBankID(IntEnum):
    SAMPLE_BANK_0 = 0
    SAMPLE_BANK_1 = 1
    SAMPLE_BANK_2 = 2
    SAMPLE_BANK_3 = 3
    SAMPLE_BANK_4 = 4
    SAMPLE_BANK_5 = 5
    SAMPLE_BANK_6 = 6
    NO_SAMPLE_BANK = 255


class EnvelopeOpcodes(IntEnum):
    DISABLE = 0
    HANG = -1
    GOTO = -2
    RESTART = -3


if __name__ == '__main__':
    pass
