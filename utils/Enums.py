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

# XML Tag enum
class XMLTags(Enum):
  ABINDEXENTRY = 'abindexentry'
  ABHEADER     = 'abheader'
  ABBANK       = 'abbank'
  ABDRUMLIST   = 'abdrumlist'
  ABSFXLIST    = 'absfxlist'
  INSTRUMENTS  = 'instruments'
  DRUMS        = 'drums'
  ENVELOPES    = 'envelopes'
  SAMPLES      = 'samples'
  ALADPCMLOOPS = 'aladpcmloops'
  ALADPCMBOOKS = 'aladpcmbooks'

# Audio sample enums
class AudioSampleCodec(IntEnum):
  CODEC_ADPCM       = 0
  CODEC_S8          = 1
  CODEC_S16_INMEM   = 2
  CODEC_SMALL_ADPCM = 3
  CODEC_REVERB      = 4
  CODEC_S16         = 5

class AudioStorageMedium(IntEnum):
  MEDIUM_RAM        = 0
  MEDIUM_UNK        = 1
  MEDIUM_CART       = 2
  MEDIUM_DISK_DRIVE = 3

if __name__ == '__main__':
  pass
