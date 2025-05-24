import struct
from enum import IntEnum
from itertools import islice

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

class Bankmeta:
  def __init__(self):
    self.address         = 0
    self.size            = 0
    self.sample_medium   = 2
    self.seq_player      = 2
    self.table_id        = 1
    self.font_id         = 255
    self.num_instruments = 16
    self.num_drums       = 64
    self.num_effects     = 0

  @classmethod
  def from_bytes(cls, data: bytes):
    self = cls()
    (
      self.sample_medium,
      self.seq_player,
      self.table_id,
      self.font_id,
      self.num_instruments,
      self.num_drums,
      self.num_effects
    ) = struct.unpack('>6B1H', data[:0x08])

    return self

  def to_bytes(self) -> bytes:
    return struct.pack('>6B1H', self.sample_medium, self.seq_player, self.table_id, self.font_id, self.num_instruments, self.num_drums, self.num_effects)

  @classmethod
  def from_xml(cls, bank_elem):
    self = cls()
    fields = bank_elem.find('abindexentry/struct').findall('field')

    self.address         = int(fields[0].attrib['value'])
    self.size            = int(fields[1].attrib['value'])
    self.sample_medium   = int(fields[2].attrib['value'])
    self.seq_player      = int(fields[3].attrib['value'])
    self.table_id        = int(fields[4].attrib['value'])
    self.font_id         = int(fields[5].attrib['value'])
    self.num_instruments = int(fields[6].attrib['value'])
    self.num_drums       = int(fields[7].attrib['value'])
    self.num_effects     = int(fields[8].attrib['value'])

    return self

  def to_dict(self):
    return {
      "name": "ABIndexentry",
      "field": [
          {"name": "Audiobank Address", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Ptr Bank (in Audiobank)", "value": str(self.address)},
          {"name": "Bank Size", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.size)},
          {"name": "Sample Medium", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "2", "value": str(self.sample_medium)},
          {"name": "Sequence Player", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "2", "value": str(self.seq_player)},
          {"name": "Audiotable", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "0", "value": str(self.table_id)},
          {"name": "Audiobank ID", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "255", "value": str(self.font_id)},
          {"name": "NUM_INST", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "NUM_INST", "value": str(self.num_instruments)},
          {"name": "NUM_DRUM", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "NUM_DRUM", "value": str(self.num_drums)},
          {"name": "NUM_SFX", "datatype": "uint16", "ispointer": "0", "isarray": "0", "meaning": "NUM_SFX", "value": str(self.num_effects)}
      ]
    }

  @property
  def attributes(self):
    return {'NUM_INST': self.num_instruments, 'NUM_DRUM': self.num_drums, 'NUM_SFX': self.num_effects, 'ATnum': self.table_id}

class Audiobank:
  def __init__(self):
    self.bankmeta = None
    self.drumlist_offset = None
    self.sfxlist_offset  = None

    self.drum_offsets       = []
    self.effect_offsets     = []
    self.instrument_offsets = []

    self.drums       = []
    self.effects     = []
    self.instruments = []

    self.envelope_registry = {}
    self.sample_registry   = {}
    self.loopbook_registry = {}
    self.codebook_registry = {}

  @classmethod
  def from_bytes(cls, bankmeta: Bankmeta, data: bytes):
    self = cls()
    self.bankmeta = bankmeta
    self.envelope_registry = {}
    self.sample_registry   = {}
    self.loopbook_registry = {}
    self.codebook_registry = {}

    self.drumlist_offset, self.sfxlist_offset = struct.unpack('>2I', data[:0x08])

    # Create drums
    self.drum_offsets = []
    for i in range(0, bankmeta.num_drums):
      offset = self.drumlist_offset + (4 * i)
      drum_offset = int.from_bytes(data[offset:offset + 0x04])
      self.drum_offsets.append(drum_offset)

    self.drums = []
    valid_drum_index = 0
    for i, addr in enumerate(self.drum_offsets):
      if addr == 0:
        self.drums.append(None)
      else:
        drum = Drum.from_bytes(valid_drum_index, addr, data, self.envelope_registry, self.sample_registry, self.loopbook_registry, self.codebook_registry)
        self.drums.append(drum)
        valid_drum_index += 1

    # Create effects
    self.effects = []
    for i in range(0, bankmeta.num_effects):
      offset = self.sfxlist_offset + (8 * i)
      chunk = data[offset:offset + 0x08]
      if chunk == b"\x00" * 8:
        self.effects.append(None)
      else:
        self.effects.append(SoundEffect.from_bytes(i, offset, data, self.sample_registry, self.loopbook_registry, self.codebook_registry))

    # Create instruments
    self.instrument_offsets = []
    for i in range(0, bankmeta.num_instruments):
      offset = 0x08 + (4 * i)
      inst_offset = int.from_bytes(data[offset:offset + 0x04])
      self.instrument_offsets.append(inst_offset)

    self.instruments = []
    valid_instrument_index = 0
    for i, addr in enumerate(self.instrument_offsets):
      if addr == 0:
        self.instruments.append(None)
      else:
        instrument = Instrument.from_bytes(valid_instrument_index, addr, data, self.envelope_registry, self.sample_registry, self.loopbook_registry, self.codebook_registry)
        self.instruments.append(instrument)
        valid_instrument_index += 1

    return self

  def to_bytes(self):
    ...

  @classmethod
  def from_xml(cls):
    ...

  def to_xml(self) -> dict:
    abbank_fields = [
      {"name": "Drum List Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABDrumList", "isarray": "0", "meaning": "Ptr Drum List", "value": str(self.drumlist_offset)},
      {"name": "SFX List Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSFXList", "isarray": "0", "meaning": "Ptr SFX List", "value": str(self.sfxlist_offset)},
      {"name": "Instrument List", "datatype": "uint32", "ispointer": "1", "ptrto": "ABInstrument", "isarray": "1", "arraylenvar": "NUM_INST", "meaning": "List of Ptrs to Insts"}
    ]

    if self.bankmeta.num_instruments != 0:
      abbank_fields[2]['element'] = []
      valid_index = 0

      for i, offset in enumerate(self.instrument_offsets):
        if offset == 0:
          abbank_fields[2]['element'].append({"datatype": "uint32", "ispointer": "1", "ptrto": "ABInstrument", "value": str(offset)})
        else:
          abbank_fields[2]['element'].append({"datatype": "uint32", "ispointer": "1", "ptrto": "ABInstrument", "value": str(offset), "index": str(valid_index)})
          valid_index += 1

    abbank_xml = [{"name": "ABBank", "field": abbank_fields}]

    abdrumlist_xml = []
    if self.bankmeta.num_drums != 0:
      drum_elements = []
      valid_index = 0

      for i, offset in enumerate(self.drum_offsets):
        if offset == 0:
          drum_elements.append({"datatype": "uint32", "ispointer": "1", "ptrto": "ABDrum", "value": str(offset)})
        else:
          drum_elements.append({"datatype": "uint32", "ispointer": "1", "ptrto": "ABDrum", "value": str(offset), "index": str(valid_index)})
          valid_index += 1

      abdrumlist_xml = [{
        "name": "ABDrumList",
        "field": [
          {"name": "Drum List", "datatype": "uint32", "ispointer": "1", "ptrto": "ABDrum", "isarray": "1", "arraylenvar": "NUM_DRUM", "element": drum_elements}
        ]
      }]

    absfxlist_xml = []
    if self.bankmeta.num_effects != 0:
      effect_elements = []

      for effect in self.effects:
        if effect is None:
          effect_elements.append(
            {
              "datatype": "ABSound", "ispointer": "0", "value": "0",
              "struct": {
                "name": "ABSound",
                "field": [
                  {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": "0"},
                  {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": "0.0"}
                ]
              }
            }
          )
        else:
          effect_elements.append(
            {
              "datatype": "ABSound", "ispointer": "0", "value": "0",
              "struct": {
                "name": "ABSound",
                "field": [
                  {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": str(effect.sample_offset), "index": str(effect.sample.index if effect.sample else -1)},
                  {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(effect.sample_tuning if effect.sample else 0.0)}
                ]
              }
            }
          )

      absfxlist_xml = [{
        "name": "ABSFXList",
        "field": [
          {"name": "SFX List", "datatype": "ABSound", "ispointer": "0", "isarray": "1", "arraylenvar": "NUM_SFX", "element": effect_elements}
        ]
      }]

    # Instruments
    instruments_xml = [inst.to_dict() for inst in self.instruments if inst is not None]

    # Drums
    drums_xml = [drum.to_dict() for drum in self.drums if drum is not None]

    # Envelopes
    envelopes_xml = [envelope.to_dict() for envelope in self.envelope_registry.values()]

    # Samples
    samples_xml = [sample.to_dict() for sample in self.sample_registry.values()]

    # Aladpcmbooks
    aladpcmbooks_xml = [codebook.to_dict() for codebook in self.codebook_registry.values()]

    # Aladpcmloops
    aladpcmloops_xml = [loopbook.to_dict() for loopbook in self.loopbook_registry.values()]

    return {
      "abbank": abbank_xml,
      "abdrumlist": abdrumlist_xml,
      "absfxlist": absfxlist_xml,
      "instruments": instruments_xml,
      "drums": drums_xml,
      "envelopes": envelopes_xml,
      "samples": samples_xml,
      "aladpcmbooks": aladpcmbooks_xml,
      "aladpcmloops": aladpcmloops_xml
    }

  @property
  def abbank_xml(self):
    return self.to_xml()["abbank"]

  @property
  def abdrumlist_xml(self):
    return self.to_xml()["abdrumlist"]

  @property
  def absfxlist_xml(self):
    return self.to_xml()["absfxlist"]

  @property
  def instruments_xml(self):
    return self.to_xml()["instruments"]

  @property
  def drums_xml(self):
    return self.to_xml()["drums"]

  @property
  def envelopes_xml(self):
    return self.to_xml()["envelopes"]

  @property
  def samples_xml(self):
    return self.to_xml()["samples"]

  @property
  def aladpcmbooks_xml(self):
    return self.to_xml()["aladpcmbooks"]

  @property
  def aladpcmloops_xml(self):
    return self.to_xml()["aladpcmloops"]

class Instrument: # struct size = 0x20
  def __init__(self):
    self.offset = 0
    self.index  = -1

    self.is_relocated    = 0
    self.key_region_low  = 0
    self.key_region_high = 127
    self.decay_index     = 255

    # Envelope Child
    self.envelope_offset = 0
    self.envelope = None

    # TunedSamples
    self.low_sample_offset = 0
    self.low_sample_tuning = 0.0

    self.prim_sample_offset = 0
    self.prim_sample_tuning = 0.0

    self.high_sample_offset = 0
    self.high_sample_tuning = 0.0

    # Sample Children
    self.low_sample  = None
    self.prim_sample = None
    self.high_sample = None

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

    return self

  def to_dict(self) -> dict:
    return {
      "address": str(self.offset), "name": f"Instrument [{self.index}]",
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

class Drum: # struct size = 0x10
  def __init__(self):
    self.offset = 0
    self.index  = -1

    self.decay_index  = 255
    self.pan          = 64
    self.is_relocated = 0
    # Padding byte between is_relocated and TunedSample

    # TunedSample structure
    self.sample_offset = 0
    self.sample_tuning = 0.0

    # Child sample structure
    self.sample = None

    # Child envelope array
    self.envelope_offset = 0
    self.envelope = None

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

    return self

  def to_dict(self) -> dict:
    return {
      "address": str(self.offset), "name": f"Drum [{self.index}]",
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

class SoundEffect:
  def __init__(self):
    self.offset = 0
    self.index  = -1

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

class Envelope:
  def __init__(self):
    self.offset = 0
    self.index  = -1

    self.points = []

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

      if delay < 0 and arg >= 0:
        break

    envelope_registry[envelope_offset] = self
    self.index = len(envelope_registry) - 1
    return self

  def to_dict(self) -> dict:
    return {
      "address": str(self.offset), "name": f"Envelope [{self.index}]",
      "fields": [
        {"name": f"Delay {i//2 + 1}", "datatype": "int16", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{self.points[i//2][0]}"}
        if i % 2 == 0 else
        {"name": f"Argument {i//2 + 1}", "datatype": "int16", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{self.points[i//2][1]}"}
        for i in range(len(self.points) * 2) # There are half the tuples as there are actual values
      ]
    }

class Sample: # struct size = 0x10
  def __init__(self):
    self.offset = 0
    self.index  = -1

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
    assert self.codec in (0, 3)
    assert self.medium == 0
    assert self.is_relocated == 0

    self.loopbook = AdpcmLoop.from_bytes(self.loopbook_offset, bank_data, loopbook_registry)
    self.codebook = AdpcmBook.from_bytes(self.codebook_offset, bank_data, codebook_registry)

    sample_registry[sample_offset] = self
    self.index = len(sample_registry) - 1
    return self

  def to_dict(self) -> dict:
    return {
      "address": str(self.offset), "name": f"Sample [{self.index}]",
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

class AdpcmLoop: # struct size = 0x10 or 0x30
  def __init__(self):
    self.offset = 0
    self.index  = -1

    self.loop_start  = 0
    self.loop_end    = 0
    self.loop_count  = 0
    self.num_samples = 0

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
    ) = struct.unpack('>4I', bank_data[loopbook_offset: loopbook_offset + 0x10])

    assert self.loop_count in (0, 0xFFFFFFFF)

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
      "address": str(self.offset), "name": f"Loop [{self.index}]",
      "struct": {
        "name": "ALADPCMLoop", "HAS_TAIL": f"{0 if self.loop_count == 0 else 1}",
        "field": [
          {"name": "Loop Start", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Loop Start", "value": str(self.loop_start)},
          {"name": "Loop End (Sample Length if Count = 0)", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Loop End", "value": str(self.loop_end)},
          {"name": "Loop Count", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Loop Count", "defaultval": "-1", "value": str(self.loop_count)},
          {"name": "Number of Samples", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.num_samples)},
          {"name": "Loopbook", "datatype": "ALADPCMTail", "ispointer": "0", "isarray": "1", "arraylenvar": "HAS_TAIL", "meaning": "Tail Data (if Loop Start != 0)", "element": loopbook_field}
        ]
      }
    }

class AdpcmBook: # struct size = 0x8 + (0x08 * order * num_predictors)
  def __init__(self):
    self.offset = 0
    self.index  = -1

    self.order          = 2
    self.num_predictors = 2

    # There are num_predictor amount of 16 value arrays
    self.predictor_arrays = []

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
      "address": str(self.offset), "name": f"Book [{self.index}]",
      "struct": {"name": "ALADPCMBook", "NUM_PRED": str(self.num_predictors),
        "field": [
          {"name": "Order", "datatype": "int32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.order)},
          {"name": "Number of Predictors", "datatype": "int32", "ispointer": "0", "isarray": "0", "meaning": "NUM_PRED", "value": str(self.num_predictors)},
          {"name": "Codebook", "datatype": "ALADPCMPredictor", "ispointer": "0", "isarray": "1", "arraylenvar": "NUM_PRED", "meaning": "Array of Predictors", "element": codebooks}
        ]
      }
    }

'''
|- Structs -|
'''
# class EnvelopePoint:
#   ''' Represents a single point of an envelope array '''
#   def __init__(self, delay: int, arg: int):
#     self.delay = delay
#     self.arg = arg

#     assert 0 <= self.arg <= 32767 or self.delay < 0

#   @classmethod
#   def from_bytes(cls, data: bytes):
#     delay, arg = struct.unpack('>2h', data[:0x04])
#     return cls(delay, arg)

#   def to_bytes(self) -> bytes:
#     return struct.pack('>2h', self.delay, self.arg)

# class Envelope:
#   ''' Represents an envelope array in OOT and MM '''
#   def __init__(self, points = None):
#     self.points = points or []

#   @classmethod
#   def from_bytes(cls, data: bytearray):
#     points = []
#     index = 0
#     while index + 4 <= len(data):
#       point = EnvelopePoint.from_bytes(data[index:index + 4])
#       points.append(point)
#       index += 4

#       if point.delay < 0 and point.arg >= 0:
#         break

#     return cls(points)

#   def to_dict(self) -> dict:
#     return {'points': [{'delay': p.delay, 'arg': p.arg} for p in self.points]}

#   @classmethod
#   def from_dict(cls, data: dict):
#     points = [EnvelopePoint(p['delay'], p['arg']) for p in data['points']]
#     return cls(points)

#   def to_bytes(self) -> bytes:
#     raw = b''.join(p.to_bytes() for p in self.points)
#     return add_padding_to_16(raw)

#   @property
#   def delay(self):
#     return [p.delay for p in self.points]

#   @property
#   def arg(self):
#     return [p.arg for p in self.points]

#   @property
#   def struct_size(self) -> int:
#     return add_padding_to_16(len(self.points) * 4)

# class AdpcmLoop:
#   def __init__(self, start: int, end: int, count: int, num_samples: int, predictors = None):
#     self.start = start
#     self.end = end
#     self.count = count
#     self.num_samples = num_samples

#     assert self.count in (0, 0xFFFFFFFF)

#     if self.count != 0:
#       if predictors is None:
#         raise ValueError()

#       assert len(predictors) == 16
#       self.predictors = tuple(predictors)

#     else:
#       assert self.start == 0
#       self.predictors = tuple([0] * 16)

#   @classmethod
#   def from_bytes(cls, data: bytes):
#     start, end, count, num_samples = struct.unpack('>4I', data[:0x10])

#     if count != 0:
#       predictors = struct.unpack('>16h', data[0x10:0x30])
#     else:
#       predictors = [0] * 16

#     return cls(start, end, count, num_samples, predictors)

#   def to_dict(self) -> dict:
#     return {
#       'loop_start': self.start,
#       'loop_end': self.end,
#       'num_samples': self.num_samples,
#       'predictors': list(self.predictors)
#     }

#   @classmethod
#   def from_dict(cls, data: dict):
#     return cls(
#       start = data['loop_start'],
#       end = data['loop_end'],
#       count = data['loop_count'],
#       samples = data['num_samples'],
#       predictors = data.get('predictors')
#     )

#   def to_bytes(self) -> bytes:
#     raw = struct.pack('>4I', self.start, self.end, self.count, self.num_samples)

#     if self.count != 0:
#       raw += struct.pack('>16h', *self.predictors)

#     return add_padding_to_16(raw)

#   @property
#   def struct_size(self) -> int:
#     base = 0x10
#     return align_to_16(base + (0x20 if self.count != 0 else 0))

# class AdpcmBook:
#   def __init__(self, order: int, num_predictors: int, predictors: list[list[int]]):
#     self.order = order
#     self.num_predictors = num_predictors
#     self.predictors = predictors

#     assert self.order == 2 # Order should always be 2

#     if num_predictors != 0:
#       if len(predictors) != num_predictors:
#         raise ValueError() # Number of arrays must match

#       for array in predictors:
#         if len(array) != 16:
#           raise ValueError() # Too few prediction coefficients in the array

#   @classmethod
#   def from_bytes(cls, data: bytes):
#     order, num_predictors = struct.unpack('>2i', data[:0x08])
#     predictor_data = data[0x08:]

#     array_iter = struct.iter_unpack('>16h', predictor_data)
#     predictors = [list(p) for p in zip(range(num_predictors), array_iter)]

#     return cls(order, num_predictors, predictors)

#   def to_dict(self) -> dict:
#     return {
#       'order': self.order,
#       'num_predictors': self.num_predictors,
#       'predictors': self.predictors
#     }

#   @classmethod
#   def from_dict(cls, data: dict):
#     return cls(
#       order = data['order'],
#       num_predictors = data['num_predictors'],
#       predictors = data['predictors']
#     )

#   def to_bytes(self) -> bytes:
#     raw = struct.pack('>2i', self.order, self.num_predictors)
#     for array in self.predictors:
#       if len(array) != 16:
#         raise ValueError() # Too few prediction coefficients in the array

#       raw += struct.pack('>16h', *array)

#     return add_padding_to_16(raw)

#   @property
#   def struct_size(self) -> int:
#     return align_to_16(8 + (8 * self.order * self.num_predictors))

# class Sample:
#   def __init__(self, unk_0: int, codec: int, medium: int, is_cached: int, is_relocated: int, size: int, sample_pointer: int, loop: int, book: int):
#     self.unk_0 = unk_0
#     self.codec = codec
#     self.medium = medium
#     self.is_cached = is_cached
#     self.is_relocated = is_relocated
#     self.size = size
#     self.sample_pointer = sample_pointer
#     self.loop = loop
#     self.book = book

#   @classmethod
#   def from_bytes(cls, data: bytes):
#     bits, sample_pointer, loop, book = struct.unpack('>4I', data[:0x10])

#     unk_0        = (bits >> 31) & 0b1
#     codec        = (bits >> 28) & 0b111
#     medium       = (bits >> 26) & 0b11
#     is_cached    = (bits >> 25) & 1
#     is_relocated = (bits >> 24) & 1
#     size         = (bits >> 0) & 0b111111111111111111111111

#     assert book != 0
#     assert loop != 0
#     assert codec in (0, 3)
#     assert medium == 0
#     assert is_relocated == 0

#     return cls(unk_0, codec, medium, is_cached, is_relocated, size, sample_pointer, loop, book)

#   def to_dict(self) -> dict:
#     return {
#       'unk_0': self.unk_0,
#       'codec': self.codec,
#       'medium': self.medium,
#       'is_cached': self.is_cached,
#       'is_relocated': self.is_relocated,
#       'size': self.size,
#       'sample_pointer': self.sample_pointer,
#       'loop': self.loop,
#       'book': self.book
#     }

#   @classmethod
#   def from_dict(cls, data: dict):
#     return cls(
#       unk_0 = data['unk_0'],
#       codec = data['codec'],
#       medium = data['medium'],
#       is_cached = data['is_cached'],
#       is_relocated = data['is_relocated'],
#       size = data['size'],
#       sample_pointer = data['sample_pointer'],
#       loop = data['loop'],
#       book = data['book']
#     )

#   def to_bytes(self) -> bytes:
#     bits  = 0
#     bits |= (self.unk_0 & 0b1) << 31
#     bits |= (self.codec & 0b111) << 28
#     bits |= (self.medium & 0b11) << 26
#     bits |= (self.is_cached & 1) << 25
#     bits |= (self.is_relocated & 1) << 24
#     bits |= (self.size & 0b111111111111111111111111)

#     raw = struct.pack('>4I', bits, self.sample_pointer, self.loop, self.book)

#     return add_padding_to_16(raw)

# class TunedSample:
#   def __init__(self, sample: int, tuning: float):
#     self.sample = sample
#     self.tuning = tuning

#   @classmethod
#   def from_bytes(cls, data: bytes):
#     sample, tuning = struct.unpack('>1I1f', data[:0x08])
#     return cls(sample, tuning)

#   def to_bytes(self) -> bytes:
#     return struct.pack('>1I1f', self.sample, self.tuning)

# class Instrument:
#   def __init__(self, is_relocated: int, key_region_low: int, key_region_high: int, decay_index: int, envelope: int, samples: list[TunedSample]):
#     self.is_relocated = is_relocated
#     self.key_region_low = key_region_low
#     self.key_region_high = key_region_high
#     self.decay_index = decay_index
#     self.envelope = envelope
#     self.samples = samples

#     assert self.is_relocated == 0

#   @classmethod
#   def from_bytes(cls, data: bytes):
#     is_relocated, key_region_low, key_region_high, decay_index, envelope = struct.unpack('>4B1I', data[:0x08])

#     samples = []
#     offset = 0x08
#     for _ in range(3):
#       sample = TunedSample.from_bytes(data[offset:offset + 0x08])
#       samples.append(sample)
#       offset += 0x08

#     return cls(is_relocated, key_region_low, key_region_high, decay_index, envelope, samples)

#   def to_dict(self) -> dict:
#     return {
#       "is_relocated": self.is_relocated,
#       "key_region_low": self.key_region_low,
#       "key_region_high": self.key_region_high,
#       "decay_index": self.decay_index,
#       "envelope": self.envelope,
#       "samples": [{"sample": s.sample, "tuning": s.tuning} for s in self.samples]
#     }

#   @classmethod
#   def from_dict(cls, data: dict):
#     samples = [TunedSample(sample['sample'], sample['tuning']) for sample in data['samples']]

#     return cls(
#       is_relocated = data['is_relocated'],
#       key_region_low = data['key_region_low'],
#       key_region_high = data['key_region_high'],
#       decay_index = data['decay_index'],
#       envelope = data['envelope'],
#       samples = samples
#     )

#   def to_bytes(self) -> bytes:
#     raw = struct.pack('>4B1I', self.is_relocated, self.key_region_low, self.key_region_high, self.decay_index, self.envelope)

#     for s in self.samples:
#       raw += s.to_bytes()

#     return add_padding_to_16(raw)

# class Drum:
#   def __init__(self, decay_index: int, pan: int, is_relocated: int, sample: TunedSample, envelope: int):
#     self.decay_index = decay_index
#     self.pan = pan
#     self.is_relocated = is_relocated
#     self.sample = sample
#     self.envelope = envelope

#     assert self.is_relocated == 0

#   @classmethod
#   def from_bytes(cls, data: bytes):
#     decay_index, pan, is_relocated = struct.unpack('>3B', data[:0x04])
#     sample = TunedSample.from_bytes(data[0x04:0x0C])
#     envelope = struct.unpack('>I', data[0x0C:0x10])[0]

#     return cls(decay_index, pan, is_relocated, sample, envelope)

#   def to_dict(self) -> dict:
#     return {
#       "decay_index": self.decay_index,
#       "pan": self.pan,
#       "is_relocated": self.is_relocated,
#       "padding": 0,
#       "sample": {
#         "sample": self.sample.sample,
#         "tuning": self.sample.tuning
#       },
#       "envelope": self.envelope
#     }

#   @classmethod
#   def from_dict(cls, data: dict):
#     return cls(
#       decay_index = data['decay_index'],
#       pan = data['pan'],
#       is_relocated = data['is_relocated'],
#       sample = TunedSample(data['sample']['sample'], data['sample']['tuning']),
#       envelope = data['envelope']
#     )

#   def to_bytes(self) -> bytes:
#     raw = struct.pack('>3B1x', self.decay_index, self.pan, self.is_relocated)
#     raw += self.sample.to_bytes()
#     raw += struct.pack('>I', self.envelope)

#     return add_padding_to_16(raw)

# class SoundEffect:
#   def __init__(self, sample: TunedSample):
#     self.sample = sample

#   @classmethod
#   def from_bytes(cls, data: bytes):
#     return cls(TunedSample(data[:0x08]))

#   def to_dict(self):
#     return {
#       "sample": self.sample.sample,
#       "tuning": self.sample.tuning
#     }

#   @classmethod
#   def from_dict(cls, data: dict):
#     return cls(TunedSample(data["sample"], data["tuning"]))

#   def to_bytes(self):
#     return self.sample.to_bytes()

'''
|- Helper Functions -|
'''
def align_to_16(data: int) -> int:
  return (data + 0x0F) & ~0x0F # or (size + 0xF) // 0x10 * 0x10

def add_padding_to_16(packed_data: bytearray) -> bytearray:
  padding: int = (-len(packed_data)) & 0x0F # or (0x10 - (size % 0x10)) % 0x10

  return packed_data + b'\x00' * padding
