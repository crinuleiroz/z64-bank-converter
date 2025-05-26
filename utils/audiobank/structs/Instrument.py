'''
### Instrument Module

This module defines the `Instrument` class, which represents the structure of an individual
instrument in an Ocarina of Time and Majora's Mask instrument bank.

Classes:
    `Instrument`:
        Represents a single instrument structure.

Functionality:
    - Parse an instrument from a binary format ('from_bytes').
    - Export instrument data back to binary format ('to_bytes').
    - Convert the instrument structure into a nested dictionary format ('to_dict') for XML serialization.
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
    This module is designed to support the reconstruction and deconstruction of instrument data
    from Ocarina of Time and Majora's Mask into SEQ64-compatible XML and binary. Used in conjunction with
    'Audiobank' and 'Bankmeta' for full instrument bank conversion.
'''

# Import child structures
from .Envelope import Envelope
from .Sample import Sample

# Import helper functions
from ...Helpers import *

class Instrument: # struct size = 0x20
  ''' Represents an instrument structure in an instrument bank '''
  def __init__(self):
    # Set the default name to be used by the class
    self.name = "Instrument"

    self.offset = 0
    self.index  = -1

    self.is_relocated    = 0
    self.key_region_low  = 0
    self.key_region_high = 127
    self.decay_index     = 255

    # Envelope array pointer
    self.envelope_offset = 0

    # TunedSample structures
    self.low_sample_offset = 0
    self.low_sample_tuning = 0.0

    self.prim_sample_offset = 0
    self.prim_sample_tuning = 0.0

    self.high_sample_offset = 0
    self.high_sample_tuning = 0.0

    # Child envelope array and sample structures
    self.envelope = None
    self.low_sample  = None
    self.prim_sample = None
    self.high_sample = None

  @staticmethod
  def _get_instrument_name(sample_names):
    ''' Finds common prefix among samples and returns the instrument name '''
    stripped_names = []
    for name in sample_names:
      if not name:
        continue

      parts = name.split(':')
      if len(parts) == 4:
        stripped_names.append(f'{parts[0]}:{parts[1]}')
      elif len(parts) == 3:
        stripped_names.append(parts[0])
      else:
        stripped_names.append(parts[0] if parts else name)

    if not stripped_names:
      return ""

    prefix = stripped_names[0]
    for name in stripped_names[1:]:
      i = 0
      while i < len(prefix) and i < len(name) and prefix[i] == name[i]:
        i += 1

      prefix = prefix[:i]

    return prefix.rstrip(':') if prefix else ""

  @classmethod
  def from_bytes(cls, inst_index: int, inst_offset: int, bank_data: bytes, envelope_registry: dict,
                 sample_registry: dict, loopbook_registry: dict, codebook_registry: dict):
    self = cls()
    self.offset = inst_offset
    self.index = inst_index

    (
      self.is_relocated,
      self.key_region_low,
      self.key_region_high,
      self.decay_index,
      self.envelope_offset,
      self.low_sample_offset,
      self.low_sample_tuning,
      self.prim_sample_offset,
      self.prim_sample_tuning,
      self.high_sample_offset,
      self.high_sample_tuning
    ) = struct.unpack('>4B 1I 1I1f 1I1f 1I1f', bank_data[inst_offset:inst_offset + 0x20])

    assert self.is_relocated == 0

    assert not (self.low_sample_offset == 0 and self.low_sample_tuning == 0.0) or self.key_region_low == 0
    assert not (self.high_sample_offset == 0 and self.high_sample_tuning == 0.0) or self.key_region_high == 127

    # Instantiate Envelope
    self.envelope = Envelope.from_bytes(self.envelope_offset, bank_data, envelope_registry) if self.envelope_offset != 0 else None

    # Instantiate Samples
    self.low_sample = Sample.from_bytes(self.low_sample_offset, bank_data, sample_registry, loopbook_registry, codebook_registry) if self.low_sample_offset != 0 else None
    self.prim_sample = Sample.from_bytes(self.prim_sample_offset, bank_data, sample_registry, loopbook_registry, codebook_registry) if self.prim_sample_offset != 0 else None
    self.high_sample = Sample.from_bytes(self.high_sample_offset, bank_data, sample_registry, loopbook_registry, codebook_registry) if self.high_sample_offset != 0 else None

    sample_names = [
      self.low_sample.name if self.low_sample else "",
      self.prim_sample.name if self.prim_sample else "",
      self.high_sample.name if self.high_sample else "",
    ]

    instrument_name = cls._get_instrument_name(sample_names)
    self.name = instrument_name if instrument_name and instrument_name != "Sample" else "Instrument"

    return self

  def to_dict(self) -> dict:
    return {
      "address": str(self.offset), "name": f"{self.name} [{self.index}]",
      "struct": {
        "name": "ABInstrument",
        "field": [
          {"name": "Relocated (Bool)", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.is_relocated)},
          {"name": "Key Region Low (Max Range)", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.key_region_low)},
          {"name": "Key Region High (Min Range)", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.key_region_high)},
          {"name": "Decay Index", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.decay_index)},
          {"name": "Envelope Pointer","datatype": "uint32","ispointer": "1","ptrto": "ABEnvelope","isarray": "0","meaning": "Ptr Envelope","value": str(self.envelope_offset),"index": str(self.envelope.index)},
          {"name": "Sample Pointer Array", "datatype": "ABSound", "ispointer": "0", "isarray": "1", "arraylenfixed": "3", "meaning": "List of 3 Sounds for Splits",
            "element": [
              {"datatype": "ABSound", "ispointer": "0", "value": "0",
                "struct": {"name": "ABSound",
                  "field": [
                    {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": str(self.low_sample_offset), "index": str(self.low_sample.index if self.low_sample else -1)},
                    {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.low_sample_tuning)}
                  ]
                }
              },
              {"datatype": "ABSound", "ispointer": "0", "value": "0",
                "struct": {"name": "ABSound",
                  "field": [
                    {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": str(self.prim_sample_offset), "index": str(self.prim_sample.index if self.prim_sample else -1)},
                    {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.prim_sample_tuning)}
                  ]
                }
              },
              {"datatype": "ABSound", "ispointer": "0", "value": "0",
                "struct": {"name": "ABSound",
                  "field": [
                    {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": str(self.high_sample_offset), "index": str(self.high_sample.index if self.high_sample else -1)},
                    {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.high_sample_tuning)}
                  ]
                }
              }
            ]
          }
        ]
      }
    }

  @classmethod
  def from_dict(cls, data: dict, envelope_registry: dict, sample_registry: int):
    self = cls()

    self.is_relocated    = data['is_relocated']
    self.key_region_low  = data['key_region_low']
    self.key_region_high = data['key_region_high']
    self.decay_index     = data['decay_index']

    self.envelope = envelope_registry[data['envelope']] if data['envelope'] != -1 else None

    self.low_sample_tuning  = data['samples'][0]['tuning']
    self.prim_sample_tuning = data['samples'][1]['tuning']
    self.high_sample_tuning = data['samples'][2]['tuning']

    self.low_sample  = sample_registry[data['samples'][0]['sample']] if data['samples'][0]['sample'] != -1 else None
    self.prim_sample = sample_registry[data['samples'][1]['sample']] if data['samples'][1]['sample'] != -1 else None
    self.high_sample = sample_registry[data['samples'][2]['sample']] if data['samples'][2]['sample'] != -1 else None

    return self

  def to_bytes(self) -> bytearray:
    return struct.pack(
      '>4B 1I 1I1f 1I1f 1I1f',
      self.is_relocated,
      self.key_region_low,
      self.key_region_high,
      self.decay_index,
      self.envelope_offset,
      self.low_sample_offset,
      self.low_sample_tuning,
      self.prim_sample_offset,
      self.prim_sample_tuning,
      self.high_sample_offset,
      self.high_sample_tuning
    )

  @classmethod
  def from_yaml(cls, instrument_dict: dict, envelope_registry: dict, sample_registry: dict):
    self = cls()

    self.is_relocated    = int(instrument_dict['relocated']) # boolean
    self.key_region_low  = instrument_dict['key region low']
    self.key_region_high = instrument_dict['key region high']
    self.decay_index     = instrument_dict['decay index']

    # Ensure envelope index defaults if not included
    envelope_index = instrument_dict.get('envelope', {}).get('index', -1)
    envelope_index = -1 if envelope_index is None else envelope_index

    self.envelope = envelope_registry[envelope_index] if envelope_index != -1 else None

    samples = instrument_dict['samples']
    def get_sample(name):
      # i: index, t: tuning, o: sample object
      s = samples.get(name, {})
      i = s.get('index', -1)
      t = s.get('tuning', 0.0)
      o = sample_registry[i] if i != -1 else None
      return o, t

    self.low_sample, self.low_sample_tuning   = get_sample('low sample')
    self.prim_sample, self.prim_sample_tuning = get_sample('prim sample')
    self.high_sample, self.high_sample_tuning = get_sample('high sample')

    return self

if __name__ == '__main__':
  pass
