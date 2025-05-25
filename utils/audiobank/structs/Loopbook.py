'''
### Loopbook Module

This module defines the `AdpcmLoop` class, which represents the structure of an individual
ADPCM loopbook in an Ocarina of Time and Majora's Mask instrument bank.

Classes:
    `AdpcmLoop`:
        Represents a single ADPCM loopbook structure.

Functionality:
    - Parse an ADPCM loopbook from a binary format ('from_bytes').
    - Export ADPCM loopbook data back to binary format ('to_bytes').
    - Convert the ADPCM loopbook structure into a nested dictionary format ('to_dict') for XML serialization.
    - Validate internal consistency of data during parsing.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `Helpers`:
        For alignment, padding, and low-level binary operations.

Intended Usage:
    This module is designed to support the reconstruction and deconstruction of ADPCM loopbook data
    from Ocarina of Time and Majora's Mask into SEQ64-compatible XML and binary. Used in conjunction with
    'Audiobank' and 'Bankmeta' for full instrument bank conversion.
'''

# Import helper functions
from ...Helpers import *

class AdpcmLoop: # struct size = 0x10 or 0x30
  ''' Represents an ADPCM loopbook structure in an instrument bank '''
  def __init__(self):
    # Set the default name to be used by the class
    self.name = "Loopbook"

    self.offset = 0
    self.index  = -1

    self.loop_start  = 0
    self.loop_end    = 0 # Becomes num_samples when start is 0
    self.loop_count  = 0 # Only 0 or -1
    self.num_samples = 0

    # Predictor array
    self.predictor_array = []

  @classmethod
  def from_bytes(cls, loopbook_offset: int, bank_data: bytes, loopbook_registry: dict):
    if loopbook_offset in loopbook_registry:
      return loopbook_registry[loopbook_offset]

    self = cls()
    self.offset = loopbook_offset

    (
      self.loop_start,
      self.loop_end,
      self.loop_count,
      self.num_samples
    ) = struct.unpack('>2I 1i 1I', bank_data[loopbook_offset: loopbook_offset + 0x10])

    assert self.loop_count in (0, -1) # (0, 0xFFFFFFFF)

    if self.loop_count != 0:
      self.predictor_array = list(struct.unpack('>16h', bank_data[loopbook_offset + 0x10:loopbook_offset + 0x30]))

    loopbook_registry[loopbook_offset] = self
    self.index = len(loopbook_registry) - 1
    return self

  def to_dict(self) -> dict:
    loopbook_field = []

    if self.loop_count != 0:
      loopbook_field = [{
        "datatype": "ALADPCMTail", "ispointer": "0", "value": "0",
        "struct": {"name": "ALADPCMTail",
          "field": [
            {"name": "data", "datatype": "int16", "ispointer": "0", "isarray": "1", "arraylenfixed": "16", "meaning": "None",
              "element": [
                {"datatype": "int16", "ispointer": "0", "value": str(predictor)}
                for predictor in self.predictor_array
              ]
            }
          ]
        }
      }]

    return {
      "address": str(self.offset), "name": f"{self.name} [{self.index}]",
      "struct": {
        "name": "ALADPCMLoop", "HAS_TAIL": f"{0 if self.loop_count == 0 else 1}",
        "field": [
          {"name": "Loop Start", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Loop Start", "value": str(self.loop_start)},
          {"name": "Loop End (Sample Length if Count = 0)", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Loop End", "value": str(self.loop_end)},
          {"name": "Loop Count", "datatype": "int32", "ispointer": "0", "isarray": "0", "meaning": "Loop Count", "defaultval": "-1", "value": str(self.loop_count)},
          {"name": "Number of Samples", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.num_samples)},
          {"name": "Loopbook", "datatype": "ALADPCMTail", "ispointer": "0", "isarray": "1", "arraylenvar": "HAS_TAIL", "meaning": "Tail Data (if Loop Start != 0)", "element": loopbook_field}
        ]
      }
    }

  @classmethod
  def from_dict(cls, data: dict):
    self = cls()

    self.loop_start  = data['loop_start']
    self.loop_end    = data['loop_end']
    self.loop_count  = data['loop_count']
    self.num_samples = data['num_samples']

    assert self.loop_count in (0, -1) # (0, 0xFFFFFFFF)

    self.predictor_array = data.get('predictor_array', [])

    return self

  def to_bytes(self) -> bytes:
    raw = struct.pack('>2I 1i 1I', self.loop_start, self.loop_end, self.loop_count, self.num_samples)

    if self.loop_count != 0:
      raw += struct.pack('>16h', *self.predictor_array)

    return add_padding_to_16(raw)

  @property
  def struct_size(self) -> int:
    base = 0x10
    return align_to_16(base + (0x20 if self.loop_count != 0 else 0))

if __name__ == '__main__':
  pass
