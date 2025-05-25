'''
### Envelope Module

This module defines the `Envelope` class, which represents the structure of an individual
EnvelopePoint array in an Ocarina of Time and Majora's Mask instrument bank.

Classes:
    `Envelope`:
        Represents a single EnvelopePoint array.

Functionality:
    - Parse an EnvelopePoint array from a binary format ('from_bytes').
    - Export EnvelopePoint array data back to binary format ('to_bytes').
    - Convert the EnvelopePoint array into a nested dictionary format ('to_dict') for XML serialization.
    - Validate internal consistency of data during parsing.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `Helpers`:
        For alignment, padding, and low-level binary operations.

Intended Usage:
    This module is designed to support the reconstruction and deconstruction of EnvelopePoint array data
    from Ocarina of Time and Majora's Mask into SEQ64-compatible XML and binary. Used in conjunction with
    'Audiobank' and 'Bankmeta' for full instrument bank conversion.
'''
# Import helper functions
from ...Helpers import *
from ...EnvelopeNames import VANILLA_ENVELOPES

class Envelope:
  ''' Represents an array of EnvelopePoints '''
  def __init__(self):
    # Set the default name to be used by the class
    self.name = "Envelope"

    self.offset = 0
    self.index  = -1

    # EnvelopePoint array
    self.points = []

  @staticmethod
  def _get_envelope_name(points):
    flat = []
    for delay, arg in points:
      flat.append(delay)
      flat.append(arg)

    for name, data in VANILLA_ENVELOPES:
      if flat == data:
        return name

    return ""

  @classmethod
  def from_bytes(cls, envelope_offset: int, bank_data: bytes, envelope_registry: dict):
    if envelope_offset in envelope_registry:
      return envelope_registry[envelope_offset]

    self = cls()
    self.offset = envelope_offset
    self.points = []

    i = envelope_offset
    while i + 4 <= len(bank_data):
      delay, arg = struct.unpack('>2h', bank_data[i:i + 4])
      self.points.append((delay, arg))
      i += 4

      if delay < 0:
        break

    envelope_name = cls._get_envelope_name(self.points)
    self.name = envelope_name if envelope_name else "Envelope"

    envelope_registry[envelope_offset] = self
    self.index = len(envelope_registry) - 1
    return self

  def to_dict(self) -> dict:
    return {
      "address": str(self.offset), "name": f"{self.name} [{self.index}]",
      "field": [
        {"name": f"Delay {i//2 + 1}", "datatype": "int16", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{self.points[i//2][0]}"}
        if i % 2 == 0 else
        {"name": f"Argument {i//2 + 1}", "datatype": "int16", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{self.points[i//2][1]}"}
        for i in range(len(self.points) * 2) # There are half the tuples as there are actual values
      ]
    }

  @classmethod
  def from_dict(cls, data: dict):
    self = cls()
    points = data.get('points', [])

    self.points = [(p['delay'], p['arg']) for p in points]
    return self

  def to_bytes(self) -> bytes:
    flat_values = []
    for delay, arg in self.points:
      flat_values.extend([delay, arg])

    raw = struct.pack('>' + 'h' * len(flat_values), * flat_values)

    return add_padding_to_16(raw)

  @property
  def struct_size(self) -> int:
    return align_to_16(len(self.points) * 4)

if __name__ == '__main__':
  pass
