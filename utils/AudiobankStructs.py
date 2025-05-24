import struct
from enum import IntEnum
from itertools import islice

import xml.etree.ElementTree as ET
from utils.XMLParser import *

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
    return struct.pack(
      '>6B1H',
      self.sample_medium,
      self.seq_player,
      self.table_id,
      self.font_id,
      self.num_instruments,
      self.num_drums,
      self.num_effects
    )

  @classmethod
  def from_xml(cls, bank_elem: xml.ElementTree):
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
    self.bank_xml = None
    self.drumlist_offset = None
    self.sfxlist_offset  = None

    self.drum_offsets       = []
    self.effect_offsets     = []
    self.instrument_offsets = []

    self.instrument_index_map = []
    self.drum_index_map       = []

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
    offset = 0

    # ABBANK Table
    abbank_data = bytearray()
    abbank_data += struct.pack('>2I', 0, 0) # temp
    for index in self.instrument_index_map:
      abbank_data += struct.pack('>I', 0) # temp

    abbank_size = align_to_16(len(abbank_data))
    abbank_offset = offset
    offset += abbank_size

    # DRUMLIST Table
    drumlist_data = bytearray()
    for index in self.drum_index_map:
      drumlist_data += struct.pack('>I', 0) # temp

    drumlist_size = align_to_16(len(drumlist_data))
    drumlist_offset = offset
    offset += drumlist_size

    # Update drumlist offset
    abbank_data[0:4] = struct.pack('>I', drumlist_offset)

    # INSTRUMENTS
    instruments_offset = offset
    for i, instrument in enumerate(self.instruments):
      instrument.offset = offset
      offset += 0x20

    instruments_size = offset - instruments_offset

    # DRUMS
    drums_offset = offset
    for i, drum in enumerate(self.drums):
      drum.offset = offset
      offset += 0x10

    drums_size = offset - drums_offset

    # SAMPLES
    samples_offset = offset
    for sample in self.sample_registry.values():
      sample.offset = offset
      offset += 0x10

    samples_size = offset - samples_offset

    # ENVELOPES
    envelopes_offset = offset
    for envelope in self.envelope_registry.values():
      envelope.offset = offset
      size = align_to_16(len(envelope.to_bytes()))
      offset += size

    envelopes_size = offset - envelopes_offset

    # LOOPBOOKS
    loopbooks_offset = offset
    for loopbook in self.loopbook_registry.values():
      loopbook.offset = offset
      size = align_to_16(len(loopbook.to_bytes()))
      offset += size

    loopbooks_size = offset - loopbooks_offset

    # CODEBOOKS
    codebooks_offset = offset
    for codebook in self.codebook_registry.values():
      codebook.offset = offset
      size = align_to_16(len(codebook.to_bytes()))
      offset += size

    codebooks_size = offset - codebooks_offset

    total_size = align_to_16(offset)

    self.update_internal_offsets()

    # WRITE TO BINARY
    binary_data = bytearray(total_size)

    binary_data[abbank_offset:abbank_offset + abbank_size] = add_padding_to_16(abbank_data)
    binary_data[drumlist_offset:drumlist_offset + drumlist_size] = add_padding_to_16(drumlist_data)

    for i, index in enumerate(self.instrument_index_map):
      if index != -1 and 0 <= index < len(self.instruments) and self.instruments[index] is not None:
        abbank_data[8 + i * 4:8 + (i + 1) * 4] = struct.pack('>I', self.instruments[index].offset)

    for i, index in enumerate(self.drum_index_map):
      if index != -1 and 0 <= index < len(self.drums) and self.drums[index] is not None:
        drumlist_data[i * 4:i * 4 + 4] = struct.pack('>I', self.drums[index].offset)

    binary_data[abbank_offset:abbank_offset + len(abbank_data)] = add_padding_to_16(abbank_data)
    binary_data[drumlist_offset:drumlist_offset + len(drumlist_data)] = add_padding_to_16(drumlist_data)

    for instrument in self.instruments:
      if instrument is not None:
        inst_bytes = instrument.to_bytes()
        binary_data[instrument.offset:instrument.offset + 0x20] = inst_bytes

    for drum in self.drums:
      if drum is not None:
        drum_bytes = drum.to_bytes()
        binary_data[drum.offset:drum.offset + 0x10] = drum_bytes

    for sample in self.sample_registry.values():
      sample_bytes = sample.to_bytes()
      binary_data[sample.offset:sample.offset + 0x10] = sample_bytes

    for envelope in self.envelope_registry.values():
      envelope_bytes = envelope.to_bytes()
      size = align_to_16(len(envelope_bytes))
      binary_data[envelope.offset:envelope.offset + size] = add_padding_to_16(envelope_bytes)

    for loopbook in self.loopbook_registry.values():
      loopbook_bytes = loopbook.to_bytes()
      size = align_to_16(len(loopbook_bytes))
      binary_data[loopbook.offset:loopbook.offset + size] = add_padding_to_16(loopbook_bytes)

    for codebook in self.codebook_registry.values():
      codebook_bytes = codebook.to_bytes()
      size = align_to_16(len(codebook_bytes))
      binary_data[codebook.offset:codebook.offset + size] = add_padding_to_16(codebook_bytes)

    return bytes(binary_data)

  @classmethod
  def from_xml(cls, bankmeta: Bankmeta, bank_elem: xml.ElementTree):
    self = cls()
    self.bankmeta = bankmeta
    self.bank_xml = bank_elem
    self.envelope_registry = {}
    self.sample_registry   = {}
    self.loopbook_registry = {}
    self.codebook_registry = {}

    abbank_elem = bank_elem.find('abbank')
    if abbank_elem is not None:
      data = parse_abbank(abbank_elem)
      self.instrument_index_map = [entry['index'] for entry in data['instrument_list']]

    drumlist_elem = bank_elem.find('abdrumlist')
    if drumlist_elem is not None:
      data = parse_drumlist(drumlist_elem)
      self.drum_index_map = [entry['index'] for entry in data]

    # Create everything in reverse order because xml uses indices instead of offsets
    loop_elem = bank_elem.find('aladpcmloops')
    if loop_elem is not None:
      for i, item in enumerate(loop_elem.findall('item')):
        data = parse_loopbook(item)
        loopbook = AdpcmLoop.from_dict(data)
        loopbook.index = i
        self.loopbook_registry[i] = loopbook

    book_elem = bank_elem.find('aladpcmbooks')
    if book_elem is not None:
      for i, item in enumerate(book_elem.findall('item')):
        data = parse_codebook(item)
        codebook = AdpcmBook.from_dict(data)
        codebook.index = i
        self.codebook_registry[i] = codebook

    sample_elem = bank_elem.find('samples')
    if sample_elem is not None:
      for i, item in enumerate(sample_elem.findall('item')):
        data = parse_sample(item)
        sample = Sample.from_dict(data, self.loopbook_registry, self.codebook_registry)
        sample.index = i
        self.sample_registry[i] = sample

    envelopes_elem = bank_elem.find('envelopes')
    if envelopes_elem is not None:
      for i, item in enumerate(envelopes_elem.findall('item')):
        data = parse_envelope(item)
        envelope = Envelope.from_dict(data)
        envelope.index = i
        self.envelope_registry[i] = envelope

    self.instruments = []
    instruments_elem = bank_elem.find('instruments')
    if instruments_elem is not None:
      for i, item in enumerate(instruments_elem.findall('item')):
        data = parse_instrument(item)
        instrument = Instrument.from_dict(data, self.envelope_registry, self.sample_registry)
        instrument.index = i
        self.instruments.append(instrument)

    self.drums = []
    drums_elem = bank_elem.find('drums')
    if drums_elem is not None:
      for i, item in enumerate(drums_elem.findall('item')):
        data = parse_drum(item)
        drum = Drum.from_dict(data, self.envelope_registry, self.sample_registry)
        drum.index = i
        self.drums.append(drum)

    return self

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

  def update_internal_offsets(self):
    for instrument in self.instruments:
      if instrument.envelope:
        instrument.envelope_offset = instrument.envelope.offset

      if instrument.low_sample:
        instrument.low_sample_offset = instrument.low_sample.offset
      if instrument.prim_sample:
        instrument.prim_sample_offset = instrument.prim_sample.offset
      if instrument.high_sample:
        instrument.high_sample_offset = instrument.high_sample.offset

    for drum in self.drums:
      if drum.sample:
        drum.sample_offset = drum.sample.offset
      if drum.envelope:
        drum.envelope_offset = drum.envelope.offset

    for effect in self.effects:
      if effect.sample:
        effect.sample_offset = effect.sample.offset

    for sample in self.sample_registry.values():
      if sample.loopbook:
        sample.loopbook_offset = sample.loopbook.offset
      if sample.codebook:
        sample.codebook_offset = sample.codebook.offset

'''
|- Structs -|
'''
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

  def to_bytes(self):
    return struct.pack('>1I1f', self.sample_offset, self.sample_tuning)

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

    self.loopbook = loopbook_registry[data['loop']]
    self.codebook = codebook_registry[data['book']]

    return self

  def to_bytes(self) -> bytes:
    bits  = 0
    bits |= (self.unk_0 & 0b1) << 31
    bits |= (self.codec & 0b111) << 28
    bits |= (self.medium & 0b11) << 26
    bits |= (self.is_cached & 1) << 25
    bits |= (self.is_relocated & 1) << 24
    bits |= (self.size & 0b111111111111111111111111)

    raw = struct.pack('>4I', bits, self.table_offset, self.loopbook_offset, self.codebook_offset)

    return add_padding_to_16(raw)

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

  @classmethod
  def from_dict(cls, data: dict):
    self = cls()

    self.loop_start  = data['loop_start']
    self.loop_end    = data['loop_end']
    self.loop_count  = data['loop_count']
    self.num_samples = data['num_samples']

    self.predictor_array = data.get('predictor_array', [])

    return self

  def to_bytes(self) -> bytes:
    raw = struct.pack('>4I', self.loop_start, self.loop_end, self.loop_count, self.num_samples)

    if self.loop_count != 0:
      raw += struct.pack('>16h', *self.predictor_array)

    return add_padding_to_16(raw)

  @property
  def struct_size(self) -> int:
    base = 0x10
    return align_to_16(base + (0x20 if self.loop_count != 0 else 0))

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

  @property
  def struct_size(self) -> int:
    return align_to_16(8 + (8 * self.order * self.num_predictors))

'''
|- Helper Functions -|
'''
def align_to_16(data: int) -> int:
  return (data + 0x0F) & ~0x0F # or (size + 0xF) // 0x10 * 0x10

def add_padding_to_16(packed_data: bytearray) -> bytearray:
  padding: int = (-len(packed_data)) & 0x0F # or (0x10 - (size % 0x10)) % 0x10

  return packed_data + b'\x00' * padding

if __name__ == '__main__':
  pass
