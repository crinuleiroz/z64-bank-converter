'''
### Sample Module

This module defines the `Sample` class, which represents the structure of an individual
sample in an Ocarina of Time and Majora's Mask instrument bank.

Classes:
    `Sample`:
        Represents a single sample structure.

Functionality:
    - Parse a sample from a binary format ('from_bytes').
    - Export sample data back to binary format ('to_bytes').
    - Convert the sample structure into a nested dictionary format ('to_dict') for XML serialization.
    - Validate internal consistency of data during parsing.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `AdpcmLoop`:
        Represents a single ADPCM loopbook structure in the instrument bank.

    `AdpcmBook`:
        Represents a single ADPCM codebook structure in the instrument bank.

    `Helpers`:
        For alignment, padding, and low-level binary operations.

    `Enums`:
        `AudioSampleCodec`:
            Enum defining supported codec types.

        `AudioStorageMedium`:
            Enum defining supported storage mediums.

Intended Usage:
    This module is designed to support the reconstruction and deconstruction of instrument bank sample data
    from Ocarina of Time and Majora's Mask into SEQ64-compatible XML and binary. Used in conjunction with
    'Audiobank' and 'Bankmeta' for full instrument bank conversion.
'''

# Import child structures
from .Loopbook import AdpcmLoop
from .Codebook import AdpcmBook

# Import helper functions
from ...Helpers import *

# Import the audio sample enums
from ...Enums import AudioSampleCodec, AudioStorageMedium

# Sample processing
SAMPLE_NAMES: dict[int, str] = {}
AUDIOTABLE_ID: int = 0
DETECTED_GAME: str = ''

class Sample: # struct size = 0x10
  ''' Represents a sample structure in an instrument bank '''
  def __init__(self):
    # Set the default name to be used by the class
    self.name = "Sample"

    self.offset = 0
    self.index  = -1

    # Bitfield
    self.bits = 0

    # Unpacked bitfield
    self.unk_0        = 0
    self.codec        = 0
    self.medium       = 0
    self.is_cached    = 0
    self.is_relocated = 0
    self.size         = 0

    self.table_offset    = 0
    self.loopbook_offset = 0
    self.codebook_offset = 0

    # Child ADPCM structures
    self.loopbook = None
    self.codebook = None

  @staticmethod
  def _get_sample_name(table_offset):
    sample_name = SAMPLE_NAMES.get(table_offset)
    return sample_name if sample_name else ""

  @classmethod
  def from_bytes(cls, sample_offset: int, bank_data: bytes, sample_registry: dict, loopbook_registry: dict, codebook_registry: dict):
    if sample_offset in sample_registry:
      return sample_registry[sample_offset]

    self = cls()
    self.offset = sample_offset

    (
      self.bits,
      self.table_offset,
      self.loopbook_offset,
      self.codebook_offset
    ) = struct.unpack('>4I', bank_data[sample_offset:sample_offset + 0x10])

    self.unk_0        = (self.bits >> 31) & 0b1
    self.codec        = (self.bits >> 28) & 0b111
    self.medium       = (self.bits >> 26) & 0b11
    self.is_cached    = (self.bits >> 25) & 1
    self.is_relocated = (self.bits >> 24) & 1
    self.size         = (self.bits >> 0) & 0b111111111111111111111111

    assert self.codebook_offset != 0
    assert self.loopbook_offset != 0
    assert AudioSampleCodec(self.codec) in (AudioSampleCodec.CODEC_ADPCM, AudioSampleCodec.CODEC_SMALL_ADPCM)
    assert AudioStorageMedium(self.medium) == AudioStorageMedium.MEDIUM_RAM
    assert not self.is_relocated

    # Get the proper offset for searching through the audio tables
    if DETECTED_GAME == 'oot':
      name_offset = add_table_oot(AUDIOTABLE_ID, self.table_offset)
    elif DETECTED_GAME == 'mm':
      name_offset = add_table_mm(AUDIOTABLE_ID, self.table_offset)

    # Get the sample name from the detected game
    sample_name = cls._get_sample_name(name_offset)
    self.name = sample_name if sample_name else "Sample"

    self.loopbook = AdpcmLoop.from_bytes(self.loopbook_offset, bank_data, loopbook_registry)
    self.codebook = AdpcmBook.from_bytes(self.codebook_offset, bank_data, codebook_registry)

    # Update the codebook and loopbook to be named after their sample
    self.loopbook.name = f"{self.name} Loopbook" if sample_name != "Sample" else "Loopbook"
    self.codebook.name = f"{self.name} Codebook" if sample_name != "Sample" else "Codebook"

    sample_registry[sample_offset] = self
    self.index = len(sample_registry) - 1
    return self

  def to_dict(self) -> dict:
    return {
      "address": str(self.offset), "name": f"{self.name} [{self.index}]",
      "struct": {"name": "ABSample",
        # Leave this comment formatted as-is, it adds a nice prettified comment to each sample item explaining the bitfield
        "__comment__": f"""
            Below are the bitfield values for each bit they represent.
            Each of these values takes up a specific amount of the 32 bits representing the u32 value.
             1 Bit(s): Unk_0       (Bit(s) 1):    {self.unk_0}
             3 Bit(s): Codec       (Bit(s) 2-4):  {AudioSampleCodec(self.codec).name} ({self.codec})
             2 Bit(s): Medium      (Bit(s) 5-6):  {AudioStorageMedium(self.medium).name} ({self.medium})
             1 Bit(s): Cached      (Bit(s) 7):    {bool(self.is_cached)} ({self.is_cached})
             1 Bit(s): Relocated   (Bit(s) 8):    {bool(self.is_relocated)} ({self.is_relocated})
            24 Bit(s): Binary size (Bit(s) 9-32): {self.size}
        """,
        "field": [
          {"name": "Bitfield", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.bits)},
          {"name": "Audiotable Address", "datatype": "uint32", "ispointer": "0", "ptrto": "ATSample", "isarray": "0", "meaning": "Sample Address (in Sample Table)", "value": str(self.table_offset)},
          {"name": "Loop Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ALADPCMLoop", "isarray": "0", "meaning": "Ptr ALADPCMLoop", "value": str(self.loopbook_offset), "index": str(self.loopbook.index)},
          {"name": "Book Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ALADPCMBook", "isarray": "0", "meaning": "Ptr ALADPCMBook", "value": str(self.codebook_offset), "index": str(self.codebook.index)}
        ]
      }
    }

  @classmethod
  def from_dict(cls, data: dict, loopbook_registry: dict, codebook_registry: dict):
    self = cls()

    self.unk_0        = data['unk_0']
    self.codec        = data['codec']
    self.medium       = data['medium']
    self.is_cached    = data['is_cached']
    self.is_relocated = data['is_relocated']
    self.size         = data['size']
    self.table_offset = data['sample_pointer']

    self.loopbook = loopbook_registry[data['loop']] if data['loop'] != -1 else None
    self.codebook = codebook_registry[data['book']] if data['book'] != -1 else None

    assert self.loopbook is not None
    assert self.codebook is not None
    assert AudioSampleCodec(self.codec) in (AudioSampleCodec.CODEC_ADPCM, AudioSampleCodec.CODEC_SMALL_ADPCM)
    assert AudioStorageMedium(self.medium) == AudioStorageMedium.MEDIUM_RAM
    assert not self.is_relocated

    return self

  def to_bytes(self) -> bytes:
    bits  = 0
    bits |= (self.unk_0 & 0b1) << 31
    bits |= (self.codec & 0b111) << 28
    bits |= (self.medium & 0b11) << 26
    bits |= (self.is_cached & 1) << 25
    bits |= (self.is_relocated & 1) << 24
    bits |= (self.size & 0b111111111111111111111111)

    return struct.pack(
      '>4I',
      bits,
      self.table_offset,
      self.loopbook_offset,
      self.codebook_offset
    )

  @classmethod
  def from_yaml(cls, sample_dict: dict, loopbook_registry: dict, codebook_registry: dict):
    self = cls()

    # Bitfield should always be present, but adding extra handling for this specifically
    self.unk_0        = sample_dict.get('bitfield', {}).get('unk_0', 0)
    self.codec        = resolve_enum_value(AudioSampleCodec, sample_dict.get('bitfield', {}).get('codec', 0))
    self.medium       = resolve_enum_value(AudioStorageMedium, sample_dict.get('bitfield', {}).get('medium', 0))
    self.is_cached    = int(sample_dict.get('bitfield', {}).get('cached', True))
    self.is_relocated = int(sample_dict.get('bitfield', {}).get('relocated', False))
    self.size         = int(sample_dict.get('bitfield', {}).get('size',0xFFFFFF))

    self.table_offset = sample_dict['audiotable offset']

    # Handling in case the indices are not present
    loopbook_index = sample_dict.get('loopbook', {}).get('index', -1)
    codebook_index = sample_dict.get('codebook', {}).get('index', -1)

    self.loopbook = loopbook_registry[loopbook_index] if loopbook_index != -1 else None
    self.codebook = codebook_registry[codebook_index] if codebook_index != -1 else None

    assert self.loopbook is not None
    assert self.codebook is not None
    assert AudioSampleCodec(self.codec) in (AudioSampleCodec.CODEC_ADPCM, AudioSampleCodec.CODEC_SMALL_ADPCM)
    assert AudioStorageMedium(self.medium) == AudioStorageMedium.MEDIUM_RAM
    assert not self.is_relocated

    return self

  def to_yaml(self) -> dict:
    return {
      "name": f"{self.name} [{self.index}]",
      "bitfield": {
        "unk_0": self.unk_0,
        "codec": AudioSampleCodec(self.codec).name,
        "medium": AudioStorageMedium(self.medium).name,
        "cached": bool(self.is_cached),
        "relocated": bool(self.is_relocated),
        "size": self.size
      },
      "audiotable offset": self.table_offset,
      "loopbook": {
        "index": self.loopbook.index
      },
      "codebook": {
        "index": self.codebook.index
      }
    }

if __name__ == '__main__':
  pass
