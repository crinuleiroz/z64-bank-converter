'''
### Codebook Module

This module defines the `AdpcmBook` class, which represents the structure of an individual
ADPCM codebook in an Ocarina of Time and Majora's Mask instrument bank.

Classes:
    `AdpcmBook`:
        Represents a single ADPCM codebook structure.

Functionality:
    - Parse an ADPCM codebook from a binary format ('from_bytes').
    - Export ADPCM codebook data back to binary format ('to_bytes').
    - Convert the ADPCM codebook structure into a nested dictionary format ('to_dict') for XML serialization.
    - Validate internal consistency of data during parsing.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `Helpers`:
        For alignment, padding, and low-level binary operations.

    `itertools`:
        `islice`:
            For slicing iterators to efficiently unpack predictor arrays without loading extra data.

Intended Usage:
    This module is designed to support the reconstruction and deconstruction of ADPCM codebook data
    from Ocarina of Time and Majora's Mask into SEQ64-compatible XML and binary. Used in conjunction with
    'Audiobank' and 'Bankmeta' for full instrument bank conversion.
'''

from itertools import islice

# Import helper functions
from ...Helpers import *

class AdpcmBook: # struct size = 0x8 + (0x08 * order * num_predictors)
  ''' Represents an ADPCM codebook structure in an instrument bank '''
  def __init__(self):
    # Set the default name to be used by the class
    self.name = "Codebook"

    self.offset = 0
    self.index  = -1

    self.order          = 2
    self.num_predictors = 2

    # Predictor arrays
    self.predictor_arrays: list[list[int]] = []

  @classmethod
  def from_bytes(cls, codebook_offset: int, bank_data: bytes, codebook_registry: dict):
    if codebook_offset in codebook_registry:
      return codebook_registry[codebook_offset]

    self = cls()
    self.offset = codebook_offset

    (
      self.order,
      self.num_predictors
    ) = struct.unpack('>2I', bank_data[codebook_offset:codebook_offset + 0x8])

    assert self.order == 2
    assert self.num_predictors in (2, 4) # need to recheck vadpcm to see how many are allowed, but generally either 2 or 4

    predictor_data = bank_data[codebook_offset + 0x08:codebook_offset + 0x08 + self.num_predictors * 0x20]
    array_iter = struct.iter_unpack('>16h', predictor_data)
    self.predictor_arrays = [list(p) for p in islice(array_iter, self.num_predictors)]

    codebook_registry[codebook_offset] = self
    self.index = len(codebook_registry) - 1
    return self

  def to_dict(self) -> dict:
    codebooks = [
      {
        "datatype": "ALADPCMPredictor", "ispointer": "0", "value": "0",
        "struct": {"name": "ALADPCMPredictor",
          "field" : [
            {"name": "data", "datatype": "int16", "ispointer": "0", "isarray": "1", "arraylenfixed": "16", "meaning": "None",
              "element": [
                {"datatype": "int16", "ispointer": "0", "value": str(predictor)}
                for predictor in predictor_array
              ]
            }
          ]
        }
      }
      for predictor_array in self.predictor_arrays
    ]

    return {
      "address": str(self.offset), "name": f"{self.name} [{self.index}]",
      "struct": {"name": "ALADPCMBook", "NUM_PRED": str(self.num_predictors),
        "field": [
          {"name": "Order", "datatype": "int32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.order)},
          {"name": "Number of Predictors", "datatype": "int32", "ispointer": "0", "isarray": "0", "meaning": "NUM_PRED", "value": str(self.num_predictors)},
          {"name": "Codebook", "datatype": "ALADPCMPredictor", "ispointer": "0", "isarray": "1", "arraylenvar": "NUM_PRED", "meaning": "Array of Predictors", "element": codebooks}
        ]
      }
    }

  @classmethod
  def from_dict(cls, data: dict):
    self = cls()

    self.order = data['order']
    self.num_predictors = data['num_predictors']
    self.predictor_arrays = data['predictor_arrays']

    return self

  def to_bytes(self) -> bytes:
    raw = struct.pack('>2i', self.order, self.num_predictors)
    for array in self.predictor_arrays:
      if len(array) != 16:
        raise ValueError() # Too few prediction coefficients in the array

      raw += struct.pack('>16h', *array)

    return add_padding_to_16(raw)

  @classmethod
  def from_yaml(cls, codebook_dict: dict):
    # Basically the same as from the XML dictionary
    self = cls()

    self.order = codebook_dict['order']
    self.num_predictors = codebook_dict['NUM_PREDICTORS']
    self.predictor_arrays = codebook_dict['predictors']

    if len(self.predictor_arrays) != self.num_predictors:
      raise ValueError() # Must have same number of arrays as there are predictors

    for pred in self.predictor_arrays:
      if len(pred) != 16:
        raise ValueError() # Must have 16 predictors

    return self

  @property
  def struct_size(self) -> int:
    return align_to_16(8 + (8 * self.order * self.num_predictors))

if __name__ == '__main__':
  pass
