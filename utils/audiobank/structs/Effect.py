'''
### Effect Module

This module defines the `SoundEffect` class, which represents the structure of an individual
sound effect in an Ocarina of Time and Majora's Mask instrument bank.

Classes:
    `SoundEffect`:
        Represents a single TunedSample structure.

Functionality:
    - Parse a sound effect from a binary format ('from_bytes').
    - Export sound effect data back to binary format ('to_bytes').
    - Convert the TunedSample structure into a nested dictionary format ('to_dict') for XML serialization.
    - Validate internal consistency of data during parsing.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `Sample`:
        Represents a single sample structure in the instrument bank.

    `Helpers`:
        For alignment, padding, and low-level binary operations.

Intended Usage:
    This module is designed to support the reconstruction and deconstruction of sound effect data
    from Ocarina of Time and Majora's Mask into SEQ64-compatible XML and binary. Used in conjunction with
    'Audiobank' and 'Bankmeta' for full instrument bank conversion.
'''

# Import child structure
from .Sample import Sample

# Import helper functions
from ...Helpers import *

class SoundEffect:
  ''' Represents a sound effect (TunedSample structure) in an instrument bank '''
  def __init__(self):
    self.offset = 0
    self.index  = -1

    # TunedSample structure
    self.sample_offset = 0
    self.sample_tuning = 0.0

    # Child sample structure
    self.sample = None

  @classmethod
  def from_bytes(cls, effect_index: int, effect_offset: int, bank_data: bytes, sample_registry: dict, loopbook_registry: dict, codebook_registry: dict):
    self = cls()
    self.offset = effect_offset
    self.index = effect_index

    (
      self.sample_offset,
      self.sample_tuning
    ) = struct.unpack('>1I1f', bank_data[effect_offset:effect_offset + 0x08])

    self.sample = Sample.from_bytes(self.sample_offset, bank_data, sample_registry, loopbook_registry, codebook_registry)

    return self

  def to_dict(self) -> dict:
    return {
      "datatype": "ABSound", "ispointer": "0", "value": "0",
      "struct": {"name": "ABSound",
        "field": [
          {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": str(self.sample_offset), "index": str(self.sample.index)},
          {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.sample_tuning)}
        ]
      }
    }

  def to_bytes(self):
    return struct.pack(
      '>1I1f',
      self.sample_offset,
      self.sample_tuning
    )

  def to_yaml(self) -> dict:
    return {
      "name": self.sample.name,
      "sample": {
        "index": self.sample.index,
        "tuning": self.sample_tuning
      }
    }

if __name__ == '__main__':
  pass
