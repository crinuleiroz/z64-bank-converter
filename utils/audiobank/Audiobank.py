'''
Audiobank Module

This module defines classes and functionality for reading, parsing, manipulating,
and exporting instrument bank data used in Ocarina of Time and Majora's Mask.

Classes:
    `Bankmeta`:
        Represents the metadata for a single instrument bank.

    `Audiobank`:
        Represents the full content of an instrument bank.

Functionality:
    - Load audio data from a binary (`from_bytes`) or XML ('from_xml') format.
    - Export bank data back to binary format or XML dictionaries.
    - Maintain internal registries for shared audio structures such as samples and envelopes.
    - Serialize bank components and update pointer references to maintain structure consistency.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `XMLParser`:
        For converting XML into useable data structures.

    `Helpers`:
        For alignment, padding, and low-level binary operations.

    `audiobank.structs`:
        Includes individual instrument bank structure representations.

Intended Usage:
    This module is intended to be used for unpacking binary OOT and MM instrument banks
    to SEQ64 XML, and packing SEQ64 XML into binary OOT and MM instrument banks.
'''

# Import Audiobank child structures
from .structs.Instrument import Instrument
from .structs.Drum import Drum
from .structs.Effect import SoundEffect
from .structs.Sample import Sample
from .structs.Envelope import Envelope
from .structs.Loopbook import AdpcmLoop
from .structs.Codebook import AdpcmBook

# Import XML parsing functions and helper functions
from ..XMLParser import *
from ..Helpers import *
from ..Enums import *

class Bankmeta:
  ''' Represents an instrument bank's metadata '''
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
  def from_xml(cls, bank_elem):
    self = cls()
    abindexentry = bank_elem.find('abindexentry')
    data = parse_abindexentry(abindexentry)

    self.address         = data['address']
    self.size            = data['size']
    self.sample_medium   = data['medium']
    self.seq_player      = data['seq_player']
    self.table_id        = data['table_id']
    self.font_id         = data['font_id']
    self.num_instruments = data['num_instruments']
    self.num_drums       = data['num_drums']
    self.num_effects     = data['num_effects']

    return self

  def to_dict(self):
    return {
      "name": "ABIndexentry",
      "field": [
          {"name": "Bank Offset in Audiobank", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Ptr Bank (in Audiobank)", "value": str(self.address)},
          {"name": "Bank Size", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.size)},
          {"name": "Sample Medium", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "2", "value": str(self.sample_medium)},
          {"name": "Sequence Player", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "2", "value": str(self.seq_player)},
          {"name": "Audiotable ID", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "0", "value": str(self.table_id)},
          {"name": "Soundfont ID", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "255", "value": str(self.font_id)},
          {"name": "NUM_INST", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "NUM_INST", "value": str(self.num_instruments)},
          {"name": "NUM_DRUM", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "NUM_DRUM", "value": str(self.num_drums)},
          {"name": "NUM_SFX", "datatype": "uint16", "ispointer": "0", "isarray": "0", "meaning": "NUM_SFX", "value": str(self.num_effects)}
      ]
    }

  @classmethod
  def from_yaml(cls, bankmeta_dict: dict):
    self = cls()

    self.address         = bankmeta_dict['address']
    self.size            = bankmeta_dict['size']
    self.sample_medium   = resolve_enum(AudioStorageMedium, bankmeta_dict['sample medium'])
    self.seq_player      = resolve_enum(SequencePlayerID, bankmeta_dict['sequence player'])
    self.table_id        = bankmeta_dict['audiotable id']
    self.font_id         = resolve_enum(SoundfontID, bankmeta_dict['soundfont id'])
    self.num_instruments = bankmeta_dict['NUM_INSTRUMENTS']
    self.num_drums       = bankmeta_dict['NUM_DRUMS']
    self.num_effects     = bankmeta_dict['NUM_EFFECTS']

    return self

  @property
  def attributes(self):
    return {'NUM_INST': self.num_instruments, 'NUM_DRUM': self.num_drums, 'NUM_SFX': self.num_effects, 'ATnum': self.table_id}

class Audiobank:
  ''' Represents an XML or binary instrument bank '''
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

    # Do not repad bytes for no reason, it randomly adds 8 extra bytes?
    binary_data[abbank_offset:abbank_offset + len(abbank_data)] = abbank_data
    binary_data[drumlist_offset:drumlist_offset + len(drumlist_data)] = drumlist_data

    # to_bytes() already pads everything, so do not repad bytes for no reason...
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
      binary_data[envelope.offset:envelope.offset + size] = envelope_bytes

    for loopbook in self.loopbook_registry.values():
      loopbook_bytes = loopbook.to_bytes()
      size = align_to_16(len(loopbook_bytes))
      binary_data[loopbook.offset:loopbook.offset + size] = loopbook_bytes

    for codebook in self.codebook_registry.values():
      codebook_bytes = codebook.to_bytes()
      size = align_to_16(len(codebook_bytes))
      binary_data[codebook.offset:codebook.offset + size] = codebook_bytes

    return bytes(binary_data) # Don't repad for no reason...

  @classmethod
  def from_xml(cls, bankmeta: Bankmeta, bank_elem):
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
      {"name": "Effect List Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSFXList", "isarray": "0", "meaning": "Ptr SFX List", "value": str(self.sfxlist_offset)},
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
          {"name": "Effect List", "datatype": "ABSound", "ispointer": "0", "isarray": "1", "arraylenvar": "NUM_SFX", "element": effect_elements}
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

  @classmethod
  def from_yaml(cls, bankmeta: object, bank_dict: dict):
    self = cls()
    self.bankmeta = bankmeta
    self.envelope_registry = {}
    self.sample_registry   = {}
    self.loopbook_registry = {}
    self.codebook_registry = {}

    # Ensure indices are correct if null pointers are not included
    instrument_map = {int(k): v for k,v in bank_dict['instrument list'].items()}
    self.instrument_index_map = [instrument_map.get(i, -1) for i in range(bankmeta.num_instruments)]

    # Ensure indices are correct if null pointers are not included
    drum_map = {int(k): v for k,v in bank_dict['drum list'].items()}
    self.drum_index_map = [drum_map.get(i, -1) for i in range(bankmeta.num_drums)]

    # Ignore effects for now, they are a bit more complex

    # Create everything in reverse order because yaml uses indices instead of offsets
    codebooks_dict = bank_dict.get('codebooks')
    if codebooks_dict is not None:
      for i, item in enumerate(codebooks_dict):
        if item is None:
          continue
        codebook = AdpcmBook.from_yaml(item)
        codebook.index = i
        self.codebook_registry[i] = codebook

    loopbooks_dict = bank_dict.get('loopbooks')
    if loopbooks_dict is not None:
      for i, item in enumerate(loopbooks_dict):
        if item is None:
          continue
        loopbook = AdpcmLoop.from_yaml(item)
        loopbook.index = i
        self.loopbook_registry[i] = loopbook

    samples_dict = bank_dict.get('samples')
    if samples_dict is not None:
      for i, item in enumerate(samples_dict):
        if item is None:
          continue
        sample = Sample.from_yaml(item, self.loopbook_registry, self.codebook_registry)
        sample.index = i
        self.sample_registry[i] = sample

    envelope_dict = bank_dict.get('envelopes')
    if envelope_dict is not None:
      for i, item in enumerate(envelope_dict):
        if item is None:
          continue
        envelope = Envelope.from_yaml(item)
        envelope.index = i
        self.envelope_registry[i] = envelope

    drums_dict = bank_dict.get('drums')
    if drums_dict is not None:
      for i, item in enumerate(drums_dict):
        if item is None:
          continue
        drum = Drum.from_yaml(item, self.envelope_registry, self.sample_registry)
        drum.index = i
        self.drums.append(drum)

    instruments_dict = bank_dict.get('instruments')
    if instruments_dict is not None:
      for i, item in enumerate(instruments_dict):
        if item is None:
          continue
        instrument = Instrument.from_yaml(item, self.envelope_registry, self.sample_registry)
        instrument.index = i
        self.instruments.append(instrument)

    return self

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

if __name__ == '__main__':
  pass
