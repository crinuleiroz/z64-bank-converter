'''
### Drum Module

This module defines the `Drum` class, which represents the structure of an individual
drum in an Ocarina of Time and Majora's Mask instrument bank.

Classes:
    `Drum`:
        Represents a single drum structure.

Functionality:
    - Parse a drum from a binary format ('from_bytes').
    - Export drum data back to binary format ('to_bytes').
    - Convert the drum structure into a nested dictionary format ('to_dict') for XML serialization.
    - Validate internal consistency of data during parsing.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `Envelope`:
        Represents a single envelope array in the instrument bank.

    `Sample`:
        Represents a single sample structure in the instrument bank.

    `Helpers`:
        For alignment, padding, and low-level binary operations.

Intended Usage:
    This module is designed to support the reconstruction and deconstruction of drum data
    from Ocarina of Time and Majora's Mask into SEQ64-compatible XML and binary. Used in conjunction with
    'Audiobank' and 'Bankmeta' for full instrument bank conversion.
'''

# Import child structures
from .Sample import Sample
from .Envelope import Envelope

# Import helper functions
from ...Helpers import *

class Drum: # struct size = 0x10
  ''' Represents a drum structure in an instrument bank '''
  def __init__(self):
    # Set the default name to be used by the class
    self.name = "Drum"

    self.offset = 0
    self.index  = -1

    self.decay_index  = 255
    self.pan          = 64
    self.is_relocated = 0
    # There is a padding byte between is_relocated and TunedSample

    # TunedSample structure
    self.sample_offset = 0
    self.sample_tuning = 0.0

    # Envelope array pointer
    self.envelope_offset = 0

    # Child sample structure and envelope array
    self.sample   = None
    self.envelope = None

  @staticmethod
  def _get_drum_name(sample_name):
    parts = sample_name.split(':')
    if len(parts) == 4:
      stripped_name = f'{parts[0]}:{parts[1]}'
    elif len(parts) == 3:
      stripped_name = parts[0]
    else:
      stripped_name = parts[0] if parts else sample_name

    return stripped_name.rstrip(':') if stripped_name else ""

  @classmethod
  def from_bytes(cls, drum_index: int, drum_offset: int, bank_data: bytes, envelope_registry: dict,
                 sample_registry: dict, loopbook_registry: dict, codebook_registry: dict):
    self = cls()
    self.offset = drum_offset
    self.index  = drum_index

    (
      self.decay_index,
      self.pan,
      self.is_relocated,
      # Padding byte
      self.sample_offset,
      self.sample_tuning,
      self.envelope_offset
    ) = struct.unpack('>3B 1x 1I1f 1I', bank_data[drum_offset:drum_offset + 0x10])

    assert self.is_relocated == 0
    assert self.sample_offset != 0 # Crashes game if 0

    self.sample = Sample.from_bytes(self.sample_offset, bank_data, sample_registry, loopbook_registry, codebook_registry)
    self.envelope = Envelope.from_bytes(self.envelope_offset, bank_data, envelope_registry) if self.envelope_offset != 0 else None

    drum_name = cls._get_drum_name(self.sample.name)
    self.name = drum_name if drum_name and drum_name != "Sample" else "Drum"

    return self

  def to_dict(self) -> dict:
    return {
      "address": str(self.offset), "name": f"{self.name} [{self.index}]",
      "struct": {"name": "ABDrum",
        "field": [
          {"name": "Decay Index", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.decay_index)},
          {"name": "Pan", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.pan)},
          {"name": "Relocated (Bool)", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.is_relocated)},
          {"name": "Padding Byte", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": "0"},
          {"name": "Drum Sound", "datatype": "ABSound", "ispointer": "0", "isarray": "0", "meaning": "Drum Sound",
            "struct": {"name": "ABSound",
              "field": [
                {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": str(self.sample_offset), "index": str(self.sample.index)},
                {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.sample_tuning)}
              ]
            }
          },
          {"name": "Envelope Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABEnvelope", "isarray": "0", "meaning": "Ptr Envelope", "value": str(self.envelope_offset), "index": str(self.envelope.index)}
        ]
      }
    }

  @classmethod
  def from_dict(cls, data: dict, envelope_registry: dict, sample_registry: dict):
    self = cls()

    self.decay_index  = data['decay_index']
    self.pan          = data['pan']
    self.is_relocated = data['is_relocated']

    self.sample_tuning = data['sample']['tuning']

    self.sample = sample_registry[data['sample']['sample']]
    self.envelope = envelope_registry[data['envelope']] if data['envelope'] != -1 else None

    return self

  def to_bytes(self) -> bytes:
    return struct.pack(
      '>3B 1x 1I1f 1I',
      self.decay_index,
      self.pan,
      self.is_relocated,
      self.sample_offset,
      self.sample_tuning,
      self.envelope_offset
    )

if __name__ == '__main__':
  pass
