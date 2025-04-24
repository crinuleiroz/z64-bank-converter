import ctypes
import struct
from dataclasses import dataclass, field
from enum import Enum, IntEnum
import xml.etree.ElementTree as xml
import os
import sys
import datetime

CURRENT_VERSION = '2025.03.09'

DATE = datetime.datetime.now().replace(microsecond=0).isoformat(' ')
DATE_FILENAME = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

"""
LAST UPDATED: 2025.03.09

WIP rewrite of bin to xml script. This rewrite aims to improve code, and allow others to easily use or modify it.
The original code was very smelly, so hopefully the code learned to take a shower with soap.

WHAT IT DOES:
  This code takes a binary bank and bankmeta file for the Nintendo 64 games and turns it back into a
  SEQ64 XML file, and eventually vice versa.

  Ctypes is used to recreate the structures as they are found in decomp's C code, and struct is used
  to unpack and pack the data into big endian format as ctypes uses the system format (little endian).
"""

"""
#-------------------------#
#        CLASSES          #
#-------------------------#
"""
class XMLTags(Enum):
  ABINDEXENTRY = 'abindexentry'
  ABHEADER     = 'abheader'
  ABBANK       = 'abbank'
  ABDRUMLIST   = 'abdrumlist'
  ABSFXLIST    = 'absfxlist'
  INSTRUMENTS  = 'instruments'
  DRUMS        = 'drums'
  ENVELOPES    = 'envelopes'
  SAMPLES      = 'samples'
  ALADPCMLOOPS = 'aladpcmloops'
  ALADPCMBOOKS = 'aladpcmbooks'

@dataclass
class XMLDataEntry:
  enum_tag:  XMLTags
  xml_tag:   str
  audiobank: object = None
  bankmeta:  object = None
  xml_list:  list[dict] = field(default_factory=list)

  def __post_init__(self):
    self.parent_tag = self.enum_tag.value

    filled_objects = [self.audiobank, self.bankmeta, self.xml_list]
    if sum(1 for obj in filled_objects if obj is not None and obj != []) != 1:
      raise ValueError("Exactly one audiobank object, bankmeta object, or XML dictionary list must be provided.")

    self._populate_xml_list()

  def _populate_xml_list(self):
    if self.bankmeta:
      self.xml_list = getattr(self.bankmeta, f'{self.parent_tag}_xml', [])
    elif self.audiobank:
      self.xml_list = getattr(self.audiobank, f'{self.parent_tag}_xml', [])

  def get_address(self) -> str:
    address_map = {
      XMLTags.ABDRUMLIST: ("drumlist", "num_drum"),
      XMLTags.ABSFXLIST:  ("sfxlist",  "num_sfx"),
    }

    if self.enum_tag in address_map:
      list_attr, num_attr = address_map[self.enum_tag]
      list_value = getattr(self.audiobank, list_attr, 0)
      if list_value != 0 and getattr(self.audiobank, num_attr, 0) != 0:
        return str(list_value)
    return ''

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

class EnvelopePoint(ctypes.Structure):
  _fields_ = [
    ("delay", ctypes.c_int16),
    ("arg",   ctypes.c_int16),
  ] # Size = 0x04

  _align_ = 0x10
  _pack_  = 0x01

  def __init__(self, data):
    self.delay, self.arg = struct.unpack('>2h', data[:0x04])

    # The argument value should never be negative, while it can be, it shouldn't be
    assert 0 <= self.arg <= 32767

  @property
  def struct_size(self):
    return ctypes.sizeof(self)

# This class handles envelopes from envelopepoint
class Envelope:
  def __init__(self, data):
    self.points = []

    index = 0
    while index + 4 <= len(data):
      env_point = EnvelopePoint(data[index:index + 4])
      self.points.append((env_point.delay, env_point.arg))
      index += 4

      if env_point.delay < 0 and env_point.arg >= 0:
        break

  @property
  def delay(self):
    return [delay[0] for delay in self.points]

  @property
  def arg(self):
    return [arg[1] for arg in self.points]

  @property
  def struct_size(self):
    return len(self.points) * 4

  @classmethod
  def get_dynamic_size(cls, data):
    points = []
    index = 0
    while index + 4 <= len(data):
      delay, arg = struct.unpack('2h', data[index:index + 4])
      points.append((delay, arg))
      index += 4

      if delay < 0 and arg >= 0:
        break

    base_size = len(points) * 4

    return align_to_16(base_size)

  @staticmethod
  def pack_data(points):
    # Handle all types of data being passed through
    if  isinstance(points, dict):
      point_values = list(points.values())
      if len(point_values) % 2 != 0:
        raise ValueError('Odd amount of pair values found, Envelopes must contain an even amount of values.')

      packed_data = b''.join([struct.pack('>2h', point_values[i], point_values[i + 1])
                              for i in range(0, len(point_values), 2)])
    elif isinstance(points[0], dict):
      packed_data = b''.join([struct.pack('>2h', *list(point.values())[:2]) for point in points])
    elif isinstance(points[0], (list, tuple)):
      packed_data = b''.join([struct.pack('>2h', delay, arg) for delay, arg in points])
    else:
      packed_data = b''.join([struct.pack('>2h', points[i], points[i + 1])
                              for i in range(0, len(points), 2)])

    return add_padding_to_16(packed_data)

class AdpcmLoop(ctypes.Structure):
  _fields_ = [
    ("start",      ctypes.c_uint32),
    ("end",        ctypes.c_uint32),
    ("count",      ctypes.c_uint32),
    ("samples",    ctypes.c_uint32),
  ] # Size = 0x10 or 0x30

  _align_ = 0x10 # Align to 16
  _pack_  = 0x01 # Ensure elements are packed without padding between

  def __init__(self, data):
    self.start, self.end, self.count, self.samples = struct.unpack('>4I', data[:0x10])

    # The loop count can only be 0 or infinite
    assert self.count in (0, 0xFFFFFFFF)

    if self.count != 0:
      self.predictors = tuple(struct.unpack('>16h', data[0x10:0x30]))
    else:
      assert self.start == 0
      self.predictors = tuple([0] * 0x10)

    assert len(self.predictors) == 0x10

  @property
  def struct_size(self):
    if self.count != 0:
      return ctypes.sizeof(self) + 0x10 * ctypes.sizeof(ctypes.c_int16)
    else:
      return ctypes.sizeof(self)

  @classmethod
  def get_dynamic_size(self, data):
    count = struct.unpack('>I', data[0x08:0x0C])[0]

    # The loop count can only be 0 or infinite
    assert count in (0, 0xFFFFFFFF)

    if count != 0:
      return ctypes.sizeof(self) + 0x10 * ctypes.sizeof(ctypes.c_int16)
    return ctypes.sizeof(self)

  @staticmethod
  def pack_data(loop_start, loop_end, loop_count, num_samples, predictors=None):
    packed_data = struct.pack('>4I', loop_start, loop_end, loop_count, num_samples)

    if loop_count != 0:
      if predictors is None:
        raise ValueError('Predictors must be provided when loop count is not zero.')

      packed_data += struct.pack('>16h', *predictors)

    return add_padding_to_16(packed_data)

class AdpcmBook(ctypes.Structure):
  _fields_ = [
    ("order", ctypes.c_int32),
    ("num_predictors", ctypes.c_int32),
  ] # Size = 0x8 + (0x08 * order * num_predictors)

  _align_ = 0x10
  _pack_  = 0x01

  def __init__(self, data):
    self.order, self.num_predictors = struct.unpack('>2i', data[:0x08])

    self.predictors = [
      tuple(v[0] for v in struct.iter_unpack('>h', data[0x08:][i * 0x20:(i + 1) * 0x20]))
      for i in range(self.num_predictors)
    ]

    if self.num_predictors != 0:
      assert len(self.predictors) == self.num_predictors

  @property
  def struct_size(self):
    return ctypes.sizeof(self) + 0x10 * ctypes.sizeof(ctypes.c_int16) * self.num_predictors

  @classmethod
  def get_dynamic_size(self, data):
    num_predictors = struct.unpack('>i', data[0x04:0x08])[0]
    return ctypes.sizeof(self) + 0x10 * ctypes.sizeof(ctypes.c_int16) * num_predictors

  @staticmethod
  def pack_data(order, num_predictors, predictors):
    packed_data = struct.pack('>2i', order, num_predictors)

    for array in predictors:
      if len(array) != 16:
        raise ValueError(f'Predictor arrays require 16 values. Found {len(array)} instead.')
      packed_data += struct.pack(f'>16h', *predictors)

    return add_padding_to_16(packed_data)

class Sample(ctypes.Structure):
  _field_ = [
    ("unk_0",        ctypes.c_uint32, 1), # First u32 is a bitfield
    ("codec",        ctypes.c_uint32, 3),
    ("medium",       ctypes.c_uint32, 2),
    ("is_cached",    ctypes.c_uint32, 1),
    ("is_relocated", ctypes.c_uint32, 1),
    ("size",         ctypes.c_uint32, 24),
    ("address",      ctypes.c_uint32),
    ("loop",         ctypes.c_uint32),
    ("book",         ctypes.c_uint32),
  ] # Size = 0x10

  def __init__(self, data):
    self.bits, self.address, self.loop, self.book = struct.unpack('>4I', data[:0x10])

    self.unk_0        = (self.bits >> 31) & 0b1
    self.codec        = AudioSampleCodec((self.bits >> 28) & 0b111)
    self.medium       = AudioStorageMedium((self.bits >> 26) & 0xb11)
    self.is_cached    = bool((self.bits >> 25) & 1)
    self.is_relocated = bool((self.bits >> 24) & 1)
    self.size         = (self.bits >> 0) & 0b111111111111111111111111

    assert self.book   != 0
    assert self.loop   != 0
    assert self.codec in (AudioSampleCodec.CODEC_ADPCM, AudioSampleCodec.CODEC_SMALL_ADPCM)
    assert self.medium == 0
    assert not self.is_relocated

  @property
  def struct_size(self):
    return ctypes.sizeof(self)

  @staticmethod
  def pack_data(unk_0, codec, medium, is_cached, is_relocated, size, address, loop, book):
    # Pack bitfields back into a single u32 value
    # Might only use size for this... unsure of how to approach this
    bits  = 0
    bits |= (unk_0 & 0b1) << 31
    bits |= (codec & 0b111) << 28
    bits |= (medium & 0b11) << 26
    bits |= (int(is_cached) & 1) << 25
    bits |= (int(is_relocated) & 1) << 24
    bits |= (size & 0b111111111111111111111111)

    packed_data = struct.pack('>4I', bits, address, loop, book)

    return add_padding_to_16(packed_data)

class TunedSample(ctypes.Structure):
  _fields_ = [
    ("address", ctypes.c_uint32),
    ("tuning",  ctypes.c_float),
  ] # Size = 0x08

  _pack_ = 0x01

  def __init__(self, data):
    self.address, self.tuning = struct.unpack('>1I1f', data[:0x08])

  @staticmethod
  def pack_data(address, tuning):
    return struct.pack('>1I1f', address, tuning)

class Instrument(ctypes.Structure):
  _fields_ = [
    ("is_relocated",    ctypes.c_ubyte),
    ("key_region_low",  ctypes.c_ubyte),
    ("key_region_high", ctypes.c_ubyte),
    ("release",         ctypes.c_ubyte),
    ("envelope",        ctypes.c_uint32),
    ("low_sample",      TunedSample),
    ("prim_sample",     TunedSample),
    ("high_sample",     TunedSample),
  ] # Size = 0x20

  _align_ = 0x10
  _pack_  = 0x01

  def __init__(self, data):
    is_relocated, self.key_region_low, self.key_region_high, self.release, self.envelope, \
    low_sample, prim_sample, high_sample = struct.unpack('>4B1I8s8s8s', data[:0x20])

    self.is_relocated = bool(is_relocated)
    self.low_sample   = TunedSample(low_sample)
    self.prim_sample  = TunedSample(prim_sample)
    self.high_sample  = TunedSample(high_sample)

    assert self.is_relocated == 0

    assert not (self.low_sample == 0 and self.low_sample.tuning == 0.0) or self.key_region_low == 0
    assert not (self.high_sample == 0 and self.high_sample.tuning == 0.0) or self.key_region_high == 127

  @property
  def size(self):
    return ctypes.sizeof(self)

  @staticmethod
  def pack_data(is_relocated, key_region_low, key_region_high, release, envelope,
                low_sample_address, low_sample_tuning, prim_sample_address, prim_sample_tuning,
                high_sample_address, high_sample_tuning):
    packed_data = struct.pack(
      '>4B1I',
      int(is_relocated),
      key_region_low,
      key_region_high,
      release,
      envelope,
    )

    packed_data += TunedSample.pack_data(low_sample_address, low_sample_tuning)
    packed_data += TunedSample.pack_data(prim_sample_address, prim_sample_tuning)
    packed_data += TunedSample.pack_data(high_sample_address, high_sample_tuning)

    return add_padding_to_16(packed_data)

class Drum(ctypes.Structure):
  _fields_ = [
    ("release",      ctypes.c_ubyte),
    ("pan",          ctypes.c_ubyte),
    ("is_relocated", ctypes.c_int16),
    ("sample",       TunedSample),
    ("envelope",     ctypes.c_uint32),
  ] # Size = 0x10

  _align_ = 0x10
  _pack_  = 0x01

  def __init__(self, data):
    self.release, self.pan, is_relocated, \
    sample_data, self.envelope = struct.unpack('>2B1h8s1I', data[:0x10])

    self.is_relocated = bool(is_relocated)
    self.sample       = TunedSample(sample_data)

    assert self.is_relocated == 0
    assert self.sample.address != 0 # Crashes game if 0

  @property
  def struct_size(self):
    return ctypes.sizeof(self)

  @staticmethod
  def pack_data(release, pan, is_relocated, sample_address, sample_tuning, envelope):
    packed_data = struct.pack('>2B1h', release, pan, int(is_relocated))
    packed_data += TunedSample.pack_data(sample_address, sample_tuning)
    packed_data += struct.pack('>1I', envelope)

    return add_padding_to_16(packed_data)

class SoundEffect(ctypes.Structure):
  _fields_ = [
    ("sample", TunedSample),
  ] # Size = 0x08

  _pack_ = 0x01

  def __init__(self, data):
    sample_data = struct.unpack('>1I1f', data[:0x08])

    self.sample = TunedSample(sample_data)

  @staticmethod
  def pack_data(address, tuning):
    return TunedSample.pack_data(address, tuning) # This is just placeholder

class BankLists(ctypes.Structure):
  _fields_ = [
    ("drumlist", ctypes.c_uint32),
    ("sfxlist",  ctypes.c_uint32),
  ]

  _align_ = 0x10
  _pack_  = 0x01

  def __init__(self, num_drum: int, num_sfx: int, num_inst: int, data: bytearray):
    self.num_inst = num_inst

    self.drumlist, self.sfxlist = struct.unpack('>2I', data[:0x08])

    self.drums = [
      struct.unpack('>I', data[self.drumlist + (i * 4) : self.drumlist + (i * 4) + 4])[0]
      for i in range(num_drum)
    ]

    self.effects = [
      # Effects are just TunedSample structs built into their pointer list
      # So just store the bytearray slices into a list
      data[self.sfxlist + (i * 8) : self.sfxlist + (i * 8) + 8]
      for i in range(num_sfx)
    ]

    self.instruments = [
      struct.unpack('>I', data[0x08 + (i * 4): 0x08 + (i * 4) + 4])[0]
      for i in range(num_inst)
    ]

  @property
  def struct_size(self):
    return ctypes.sizeof(self) + self.num_inst * ctypes.sizeof(ctypes.c_uint32)

  @classmethod
  def get_dynamic_size(self, num_inst):
    return ctypes.sizeof(self) + num_inst * ctypes.sizeof(ctypes.c_uint32)

  @staticmethod
  def pack_data():
    return NotImplementedError

class Audiobank:
  """
  Represent a binary audiobank, parsing relevant information from binary data.

  Attributes:
      num_drum (int): Number of instruments in the bank.
      num_sfx (int): Number of effects in the bank.
      num_inst (int): Number of instruments in the bank.
      data (bytearray): The binary bank data.
      drums_xml (dict): A dictionary containing drums in XML-ready format.
      instruments_xml (dict): A dictionary containing instruments in XML-ready format.
      effects_xml (dict): A dictionary containing effects in XML-ready format.
      envelopes_xml (dict): A dictionary containing envelopes in XML-ready format.
      samples_xml (dict): A dictionary containing samples in XML-ready format.
      loops_xml (dict): A dictionary containing loops in XML-ready format.
      books_xml (dict): A dictionary containing books in XML-ready format.
      drum_offsets (list): A list of drum offsets in the binary.
      effect_offsets (list): A list of effect offsets in the binary.
      inst_offsets (list): A list of instrument offsets in the binary.
      envelope_offsets (list): A list of envelope offsets in the binary.
      sample_offsets (list): A list of sample offsets in the binary.
      loop_offsets (list): A list of loop offsets in the binary.
      book_offsets (list): A list of book offsets in the binary.

  Methods:
      __init__(num_drum: int, num_sfx: int, num_inst: int, data: bytearray): Initializes the Audiobank object.
      unpack_binary(): Parses and stores unpacked binary data in a structured format.
  """
  def __init__(self, num_drum: int, num_sfx: int, num_inst: int, data: bytearray):
    self.num_drum = num_drum
    self.num_sfx = num_sfx
    self.num_inst = num_inst
    self.data = data

    # Init the XML lists
    self.drums_xml = []
    self.instruments_xml = []
    self.effects_xml = []
    self.envelopes_xml = []
    self.samples_xml = []
    self.aladpcmloops_xml = []
    self.aladpcmbooks_xml = []

  def unpack_binary(self) -> None:
    """
    Parses the bank binary and unpacks the binary data into lists and dictionaries.
    """
    lists = BankLists(self.num_drum, self.num_sfx, self.num_inst, self.data)

    self.drumlist       = lists.drumlist
    self.sfxlist        = lists.sfxlist
    self.drum_offsets   = lists.drums
    self.effect_offsets = lists.effects
    self.inst_offsets   = lists.instruments

    # Initialize offset lists
    self.sample_offsets   = []
    self.envelope_offsets = []
    self.loop_offsets     = []
    self.book_offsets     = []

    # Init indexes ensuring address 0 returns -1 for index
    self.instrument_indexes: dict[int, int] = {0: -1,}
    self.drum_indexes:       dict[int, int] = {0: -1,}
    self.envelope_indexes:   dict[int, int] = {0: -1,}
    self.sample_indexes:     dict[int, int] = {0: -1,}
    self.loop_indexes:       dict[int, int] = {0: -1,}
    self.book_indexes:       dict[int, int] = {0: -1,}

    # Create the XML dictionary for abbank
    self.abbank_xml = [
      {"name": "ABBank",
        "field": [
          {"name": "Drum List Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABDrumList", "isarray": "0", "meaning": "Ptr Drum List", "value": f"{lists.drumlist}"},
          {"name": "SFX List Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSFXList", "isarray": "0", "meaning": "Ptr SFX List", "value": f"{lists.sfxlist}"},
          {"name": "Instrument List", "datatype": "uint32", "ispointer": "1", "ptrto": "ABInstrument", "isarray": "1", "arraylenvar": "NUM_INST", "meaning": "List of Ptrs to Insts"}
        ]
      }
    ]

    # Only append element list if NUM_INST is not 0
    if self.num_inst != 0:
      self.abbank_xml[0]['field'][2]['element'] = [
        {"datatype": "uint32", "ispointer": "1", "ptrto": "ABInstrument", "value": f"{address}", "index": f"{i_index}"}
        for address in lists.instruments
        for i_index in [index_addresses(self.instrument_indexes, address)]
      ]

    # Only create the XML dictionary for abdrumlist if NUM_DRUM is not 0
    if self.num_drum != 0:
      self.abdrumlist_xml = [
        {"name": "ABDrumList",
          "field": [
            {"name": "Drum List", "datatype": "uint32", "ispointer": "1", "ptrto": "ABDrum", "isarray": "1", "arraylenvar": "NUM_DRUM",
              "element": [
                {"datatype": "uint32", "ispointer": "1", "ptrto": "ABDrum", "value": f"{address}", "index": f"{d_index}"}
                for address in lists.drums
                for d_index in [index_addresses(self.drum_indexes, address)]
              ]
            }
          ]
        }
      ]

    # Only create the XML dictionary for absfxlist if NUM_SFX is not 0
    if self.num_sfx != 0:
      self.absfxlist_xml = [
        {"name": "ABSFXList",
          "field": [
            {"name": "SFX List", "datatype": "ABSound", "ispointer": "0", "isarray": "1", "arraylenvar": "NUM_SFX",
              "element": []
            }
          ]
        }
      ]

    parse_configs = [
      { # SFX parse config
        "item_type": "effect",
        "item_list": lists.effects,
        "item_func": lambda i: SoundEffect(lists.effects[i]),
        "attr_map":  [('sample.address', self.sample_offsets)],
        "xml_list":  self.absfxlist_xml[0]['field'][0]['element'] if self.num_sfx != 0 else [],
        "xml_func":  self.generate_effect_xml,
        "num_items": self.num_sfx
      },
      { # Drum parse config
        "item_type": "drum",
        "item_list": lists.drums,
        "item_func": lambda i: Drum(read_at_offset(self.data, lists.drums[i], 0x10)),
        "attr_map":  [('envelope', self.envelope_offsets),
                      ('sample.address', self.sample_offsets)],
        "xml_list":  self.drums_xml,
        "xml_func":  self.generate_drum_xml,
        "num_items": self.num_drum
      },
      { # Instrument parse config
        "item_type": "instrument",
        "item_list": lists.instruments,
        "item_func": lambda i: Instrument(read_at_offset(self.data, lists.instruments[i], 0x20)),
        "attr_map":  [('envelope',    self.envelope_offsets),
                      ('low_sample.address',  self.sample_offsets),
                      ('prim_sample.address', self.sample_offsets),
                      ('high_sample.address', self.sample_offsets)],
        "xml_list":  self.instruments_xml,
        "xml_func":  self.generate_inst_xml,
        "num_items": self.num_inst
      },
      { # Envelope parse config
        "item_type": "envelope",
        "item_list": self.envelope_offsets,
        "item_func": lambda i: Envelope(read_at_offset(self.data, offset := self.envelope_offsets[i], Envelope.get_dynamic_size(self.data[offset:]))),
        "attr_map":  [],
        "xml_list":  self.envelopes_xml,
        "xml_func":  self.generate_envelope_xml
      },
      { # Sample parse config
        "item_type": "sample",
        "item_list": self.sample_offsets,
        "item_func": lambda i: Sample(read_at_offset(self.data, self.sample_offsets[i], 0x10)),
        "attr_map":  [('loop', self.loop_offsets),
                      ('book', self.book_offsets)],
        "xml_list":  self.samples_xml,
        "xml_func":  self.generate_sample_xml
      },
      { # Loopbook parse config
        "item_type": 'loop',
        "item_list": self.loop_offsets,
        "item_func": lambda i: AdpcmLoop(read_at_offset(self.data, offset := self.loop_offsets[i], AdpcmLoop.get_dynamic_size(self.data[offset:offset + 0x10]))),
        "attr_map":  [],
        "xml_list":  self.aladpcmloops_xml,
        "xml_func":  self.generate_loop_xml
      },
      { # Codebook parse config
        "item_type": "book",
        "item_list": self.book_offsets,
        "item_func": lambda i: AdpcmBook(read_at_offset(self.data, offset := self.book_offsets[i], AdpcmBook.get_dynamic_size(self.data[offset:offset + 0x08]))),
        "attr_map":  [],
        "xml_list":  self.aladpcmbooks_xml,
        "xml_func":  self.generate_book_xml
      }
    ]

    for config in parse_configs:
      if config['item_type'] in ['effect', 'drums', 'instrument'] and config['num_items'] == 0:
        continue

      self.parse_items(
        item_type=config['item_type'], item_list=config['item_list'], item_func=config['item_func'],
        attr_map=config['attr_map'],   xml_list=config['xml_list'],   xml_func=config['xml_func']
      )

  def generate_effect_xml(self, effect, i, address):
    s_index = index_addresses(self.sample_indexes, effect.sample.address)
    return {
        "datatype": "ABSound", "ispointer": "0", "value": "0",
        "struct": {"name": "ABSound",
          "field": [
            {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": f"{effect.sample.address}", "index": f"{s_index}"},
            {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{effect.sample.tuning}"}
          ]
        }
      }

  def generate_drum_xml(self, drum, i, address):
    s_index = index_addresses(self.sample_indexes, drum.sample.address)
    e_index = index_addresses(self.envelope_indexes, drum.envelope)
    return {"address": f"{address}", "name": f"Drum [{i}]",
          "struct": {"name": "ABDrum",
            "field": [
              {"name": "Release Rate", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{drum.release}"},
              {"name": "Pan", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{drum.pan}"},
              {"name": "Relocated (Bool)", "datatype": "uint16", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{drum.is_relocated}"},
              {"name": "Drum Sound", "datatype": "ABSound", "ispointer": "0", "isarray": "0", "meaning": "Drum Sound",
                "struct": {"name": "ABSound",
                  "field": [
                    {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": f"{drum.sample.address}", "index": f"{s_index}"},
                    {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{drum.sample.tuning}"}
                  ]
                }
              },
              {"name": "Envelope Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABEnvelope", "isarray": "0", "meaning": "Ptr Envelope", "value": f"{drum.envelope}", "index": f"{e_index}"}
            ]
          }
        }

  def generate_inst_xml(self, instrument, i, address):
    s_low_index, s_prim_index, s_high_index = index_addresses(self.sample_indexes, instrument.low_sample.address, instrument.prim_sample.address, instrument.high_sample.address)
    e_index = index_addresses(self.envelope_indexes, instrument.envelope)
    return {"address": f"{address}", "name": f"Instrument [{i}]",
          "struct": {
            "name": "ABInstrument",
            "field": [
              {"name": "Relocated (Bool)", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{instrument.is_relocated}"},
              {"name": "Key Region Low (Max Range)", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{instrument.key_region_low}"},
              {"name": "Key Region High (Min Range)", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{instrument.key_region_high}"},
              {"name": "Release Rate", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{instrument.release}"},
              {"name": "Envelope Pointer","datatype": "uint32","ispointer": "1","ptrto": "ABEnvelope","isarray": "0","meaning": "Ptr Envelope","value": f"{instrument.envelope}","index": f"{e_index}"},
              {"name": "Sample Pointer Array", "datatype": "ABSound", "ispointer": "0", "isarray": "1", "arraylenfixed": "3", "meaning": "List of 3 Sounds for Splits",
                "element": [
                  {"datatype": "ABSound", "ispointer": "0", "value": "0",
                    "struct": {"name": "ABSound",
                      "field": [
                        {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": f"{instrument.low_sample.address}", "index": f"{s_low_index}"},
                        {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{instrument.low_sample.tuning}"}
                      ]
                    }
                  },
                  {"datatype": "ABSound", "ispointer": "0", "value": "0",
                    "struct": {"name": "ABSound",
                      "field": [
                        {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": f"{instrument.prim_sample.address}", "index": f"{s_prim_index}"},
                        {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{instrument.prim_sample.tuning}"}
                      ]
                    }
                  },
                  {"datatype": "ABSound", "ispointer": "0", "value": "0",
                    "struct": {"name": "ABSound",
                      "field": [
                        {"name": "Sample Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ABSample", "isarray": "0", "meaning": "Ptr Sample", "value": f"{instrument.high_sample.address}", "index": f"{s_high_index}"},
                        {"name": "Sample Tuning", "datatype": "float32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{instrument.high_sample.tuning}"}
                      ]
                    }
                  }
                ]
              }
            ]
          }
        }

  def generate_envelope_xml(self, envelope, i, address):
    return {"address": f"{address}", "name": f"Envelope [{i}]",
          "fields": [
            {"name": f"Delay {i//2 + 1}", "datatype": "int16", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{envelope.delay[i//2]}"}
            if i % 2 == 0 else
            {"name": f"Argument {i//2 + 1}", "datatype": "int16", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{envelope.arg[i//2]}"}
            for i in range(len(envelope.points) * 2) # There are half the tuples as there are actual values
          ]
        }

  def generate_sample_xml(self, sample, i, address):
    l_index = index_addresses(self.loop_indexes, sample.loop)
    b_index = index_addresses(self.book_indexes, sample.book)
    return {"address": f"{address}", "name": f"Sample [{i}]",
          "struct": {"name": "ABSample",
            # Leave this comment formatted as-is, it adds a nice prettified comment to each sample item explaining the bitfield
            "__comment__": f"""
             Below are the bitfield values for each bit they represent.
             Each of these values takes up a specific amount of the 32 bits representing the u32 value.
              1 Bit(s): Unk_0       (Bit(s) 1):    {sample.unk_0}
              3 Bit(s): Codec       (Bit(s) 2-4):  {sample.codec.name} ({sample.codec.value})
              2 Bit(s): Medium      (Bit(s) 5-6):  {sample.medium.name} ({sample.codec.value})
              1 Bit(s): Cached      (Bit(s) 7):    {sample.is_cached} ({int(sample.is_cached)})
              1 Bit(s): Relocated   (Bit(s) 8):    {sample.is_relocated} ({int(sample.is_relocated)})
             24 Bit(s): Binary size (Bit(s) 9-32): {sample.size}
         """,
            "field": [
              {"name": "Bitfield", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{sample.bits}"},
              {"name": "Audiotable Address", "datatype": "uint32", "ispointer": "0", "ptrto": "ATSample", "isarray": "0", "meaning": "Sample Address (in Sample Table)", "value": f"{sample.address}"},
              {"name": "Loop Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ALADPCMLoop", "isarray": "0", "meaning": "Ptr ALADPCMLoop", "value": f"{sample.loop}", "index": f"{l_index}"},
              {"name": "Book Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ALADPCMBook", "isarray": "0", "meaning": "Ptr ALADPCMBook", "value": f"{sample.book}", "index": f"{b_index}"}
            ]
          }
        }

  def generate_loop_xml(self, loop, i, address):
    loopbook_field = []

    if loop.count != 0:
      loopbook_field = [
        {"datatype": "ALADPCMTail", "ispointer": "0", "value": "0",
          "struct": {"name": "ALADPCMTail",
            "field": [
              {"name": "data", "datatype": "int16", "ispointer": "0", "isarray": "1", "arraylenfixed": "16", "meaning": "None",
                "element": [
                  {"datatype": "int16", "ispointer": "0", "value": f"{predictor}"}
                  for predictor in loop.predictors
                ]
              }
            ]
          }
        }
      ]

    return {"address": f"{address}", "name": f"Loop [{i}]",
              "struct": {
                "name": "ALADPCMLoop", "HAS_TAIL": f"{0 if loop.count == 0 else 1}",
                "field": [
                  {"name": "Loop Start", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Loop Start", "value": f"{loop.start}"},
                  {"name": "Loop End (Sample Length if Count = 0)", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Loop End", "value": f"{loop.end}"},
                  {"name": "Loop Count", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "Loop Count", "defaultval": "-1", "value": f"{loop.count}"},
                  {"name": "Number of Samples", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{loop.samples}"},
                  {"name": "Loopbook", "datatype": "ALADPCMTail", "ispointer": "0", "isarray": "1", "arraylenvar": "HAS_TAIL", "meaning": "Tail Data (if Loop Start != 0)", "element": loopbook_field}
                ]
              }
            }

  def generate_book_xml(self, book, i, address):
    codebooks = [
      {"datatype": "ALADPCMPredictor", "ispointer": "0", "value": "0",
        "struct": {"name": "ALADPCMPredictor",
          "field" : [
            {"name": "data", "datatype": "int16", "ispointer": "0", "isarray": "1", "arraylenfixed": "16", "meaning": "None",
              "element": [
                {"datatype": "int16", "ispointer": "0", "value": f"{predictor}"}
                for predictor in predictors
              ]
            }
          ]
        }
      }
      for predictors in book.predictors
    ]

    return {"address": f"{address}", "name": f"Book [{i}]",
              "struct": {"name": "ALADPCMBook", "NUM_PRED": f"{book.num_predictors}",
                "field": [
                  {"name": "Order", "datatype": "int32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{book.order}"},
                  {"name": "Number of Predictors", "datatype": "int32", "ispointer": "0", "isarray": "0", "meaning": "NUM_PRED", "value": f"{book.num_predictors}"},
                  {"name": "Codebook", "datatype": "ALADPCMPredictor", "ispointer": "0", "isarray": "1", "arraylenvar": "NUM_PRED", "meaning": "Array of Predictors", "element": codebooks}
                ]
              }
            }

  def parse_items(self, item_type, item_list, item_func, attr_map, xml_list, xml_func):
    for i, address in enumerate(item_list):
      if item_type != 'effect' and address == 0:
        continue

      item = item_func(i)

      for attribute, offset_list in attr_map:
        if '.' in attribute:
          value = get_nested_attr(item, attribute)
        else:
          value = getattr(item, attribute)

        append_if_unique(value, offset_list)

      xml_list.append(xml_func(item, i, address))

class Bankmeta:
  """
  Represents the metadata for an audiobank, parsing its size and other relevant information from binary data.

  Attributes:
      address (int): Placeholder for bank address in the audiobank entries.
      size (int): The size of the bank binary.
      medium (int): The medium samples are stored in.
      player (int): The sequence player the audiobank uses.
      audiotable (int): The audiotable ID where samples the bank uses are stored.
      bank_id (int): The ID of the audiobank.
      num_inst (int): The number of instruments in the bank.
      num_drum (int): The number of drums in the bank.
      attributes (dict): A dictionary containing the parsed attributes.
      abindexentry (list): A list of dictionaries to be converted to XML.

  Methods:
      __init__(size: int, data: bytearray): Initializes the Bankmeta object.
      unpack_binary(): Parses data and stores unpacked binary data in a structured format.
  """
  def __init__(self, size: int, data: bytearray):
    """
    Initializes the Bankmeta object by unpacking binary data and storing the relevant attributes.

    Args:
        size (int): The size of the bank binary.
        data (bytearray): The binary data to extract information from.
    """
    self.address = 0    # This can not be gotten because the bankmeta file does not contain it
    self.size    = size # Size of the bank binary

    self.medium, self.player, self.audiotable, self.bank_id, \
      self.num_inst, self.num_drum, self.num_sfx = struct.unpack('>6B1H', data[:0x0C])

  def unpack_binary(self) -> None:
    """
    Parses the attributes of the Bankmeta and stores them into dictionaries to create XML.
    """
    # This data needs to be added to the bank's root element
    self.attributes = {'NUM_INST': self.num_inst, 'NUM_DRUM': self.num_drum, 'NUM_SFX': self.num_sfx, 'ATnum': self.audiotable}

    # Create an XML dictionary for the bankmeta file
    self.abindexentry_xml = [
      {"name": "ABIndexentry",
        "field": [
          {"name": "Audiobank Address", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "Ptr Bank (in Audiobank)", "value": f"{self.address}"},
          {"name": "Bank Size", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": f"{self.size}"},
          {"name": "Sample Medium", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "2", "value": f"{self.medium}"},
          {"name": "Sequnce Player", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "2", "value": f"{self.player}"},
          {"name": "Audiotable", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "0", "value": f"{self.audiotable}"},
          {"name": "Audiobank ID", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "None", "defaultval": "255", "value": f"{self.bank_id}"},
          {"name": "NUM_INST", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "NUM_INST", "value": f"{self.num_inst}"},
          {"name": "NUM_DRUM", "datatype": "uint8", "ispointer": "0", "isarray": "0", "meaning": "NUM_DRUM", "value": f"{self.num_drum}"},
          {"name": "NUM_SFX", "datatype": "uint16", "ispointer": "0", "isarray": "0", "meaning": "NUM_SFX", "value": f"{self.num_sfx}"}
        ]
      }
    ]

"""
#-------------------------#
#        FUNCTIONS        #
#-------------------------#
"""
def read_binary(filename: str) -> bytearray:
  with open(filename, 'rb') as file:
    binary = bytearray(file.read())

  return binary

def align_to_16(data: int) -> int:
  """
  Aligns the given data size to the nearest multiple of 16.

  Args:
      data (int): The data to be aligned.

  Returns:
      int: The aligned data size.
  """
  return (data + 0x0F) & ~0x0F # or (size + 0xF) // 0x10 * 0x10

def add_padding_to_16(packed_data: bytearray) -> bytearray:
  """
  Adds padding to the packed data to make its length a multiple of 16.

  Args:
      packed_data (bytearray): The bytearray to which padding will be added.

  Returns:
      bytearray: The original packed data with padding added.
  """
  padding: int = (-len(packed_data)) & 0x0F # or (0x10 - (size % 0x10)) % 0x10

  return packed_data + b'\x00' * padding

def read_at_offset(data: bytearray, offset: int, length: int) -> bytearray:
  """
  Reads a slice of data at the specified offset with a given length.

  Args:
      data (bytearray): The bytearray to read from.
      offset (int): The start position in the bytearray.
      length (int): The number of bytes to read.

  Returns:
      bytearray: A sliced portion of the original data.
  """
  return data[offset:offset + length]

def get_nested_attr(obj, attr_chain):
  for attr in attr_chain.split('.'):
    obj = getattr(obj, attr)
  return obj

def append_if_unique(value: int, target_list: list[int]) -> None:
  """
  Appends a non-zero value to a the target list if the value is not already in the list.

  Args:
      value (any): The value to check and append.
      target_list (list): The list to append the value to.
  """
  if value not in target_list and value != 0:
      target_list.append(value)

def index_addresses(output: dict[int, int], *addresses: int) -> int | tuple[int, ...]:
  """
  Adds addresses to a dictionary and returns their indices.

  Args:
      output (dict[int, int]): The dictionary to store addresses and their indices.
      *addresses (int): One or more addresses to be indexed.

  Returns:
      int | tuple[int, ...]: A tuple of indices for multiple addresses, or a single index for a single address.
  """
  # if len(addresses) == 1:
  #   address = addresses[0]
  #   if address != 0 and address not in output:
  #     output[address] = (len(output) - 1)

  #   return output[address]

  # indexes = []
  # for address in addresses:
  #   if address != 0 and address not in output:
  #     output[address] = (len(output) - 1)

  #   indexes.append(output[address])

  # return tuple(indexes)
  indexes = []

  current_index = len(output) - 1

  for address in addresses:
    if address == 0:
      indexes.append(-1)
      continue

    if address not in output:
      current_index += 1
      output[address] = current_index

    indexes.append(output[address])

  return tuple(indexes) if len(indexes) > 1 else indexes[0]

"""
# WRITE TO XML
"""
def dict_to_xml(tag: str, d: dict, parent: xml.Element = None) -> xml.Element:
  """
  Converts a dictionary to an XML element, optionally adding it to a parent element.

  Args:
      tag (str): The tag name for the XML element.
      d (dict[str, any]): The dictionary to convert to XML.
      parent (xml.Element, optional): The parent XML element to append to.

  Returns:
      xml.Element: The generated XML element.
  """
  element = xml.Element(tag)

  for key, value in d.items():
    # Create a comment if the key is "__comment__"
    if key == "__comment__":
      comment = xml.Comment(value)
      element.append(comment)

    # Recursion if the value is a dict
    elif isinstance(value, dict):
      dict_to_xml(key, value, element)

    # Create multiple separate elements for each list entry
    elif isinstance(value, list):
      for item in value:
        # The items should be dictionaries, so more recursion
        child = dict_to_xml(key, item)
        element.append(child)

    else:
      element.set(key, str(value) if value is not None else "")

  # Add each separate item to the parent element
  # e.g. prevents multiple <instruments> tags for each instrument <item> tag
  if parent is not None:
    parent.append(element)

  return element

def create_xml_bank(filename: str, bankmeta: object, audiobank: object) -> None:
  xml_root = xml.Element('bank')

  for key, value in bankmeta.attributes.items():
    xml_root.set(key, str(value))

  xml_tree = xml.ElementTree(xml_root)
  xml_comment = xml.Comment(f'\n      DATE CREATED: {DATE}\n\n      This bank was created from a binary bank file, because of this there may be errors or differences from the original bank!\n  ')

  # The ordering of data does not matter, just as long as the required structures are present.
  # All structures other than the random always empty <sfx> tag are required, even if empty.
  xml_data = [
    XMLDataEntry(XMLTags.ABINDEXENTRY, 'struct', bankmeta),
    XMLDataEntry(XMLTags.ABHEADER,     'struct', [{"name": 'ABHeader'}]),
    XMLDataEntry(XMLTags.ABBANK,       'struct', audiobank),
    XMLDataEntry(XMLTags.ABDRUMLIST,   'struct', audiobank),
    XMLDataEntry(XMLTags.ABSFXLIST,    'struct', audiobank),
    XMLDataEntry(XMLTags.INSTRUMENTS,  'item',   audiobank),
    XMLDataEntry(XMLTags.DRUMS,        'item',   audiobank),
    XMLDataEntry(XMLTags.ENVELOPES,    'item',   audiobank),
    XMLDataEntry(XMLTags.SAMPLES,      'item',   audiobank),
    XMLDataEntry(XMLTags.ALADPCMBOOKS, 'item',   audiobank),
    XMLDataEntry(XMLTags.ALADPCMLOOPS, 'item',   audiobank)
  ]

  for entry in xml_data:
    element = xml.Element(entry.parent_tag)

    address = entry.get_address()
    if address:
      element.set("address", address)

    for item in entry.xml_list:
      dict_to_xml(entry.xml_tag, item, element)

    xml_root.append(element)

  with open(f'BANK_{filename}_{DATE_FILENAME}.xml', 'wb') as f:
    xml.indent(xml_tree)
    f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write(xml.tostring(xml_comment) + b'\n')
    xml_tree.write(f, encoding='utf-8', xml_declaration=False)

"""
#-------------------------#
# PUBLIC STATIC VOID MAIN #
#-------------------------#
"""
def main() -> None:
  # This is temporary until I add proper file checking
  bank_bin     = sys.argv[1]
  bankmeta_bin = sys.argv[2]

  filename = os.path.basename(os.path.splitext(sys.argv[1])[0])

  bank_data     = read_binary(bank_bin)
  bankmeta_data = read_binary(bankmeta_bin)

  # Create the bankmeta object
  bankmeta = Bankmeta(os.path.getsize(bank_bin), bankmeta_data)
  bankmeta.unpack_binary()

  # Create the audiobank object
  audiobank = Audiobank(bankmeta.num_drum, bankmeta.num_sfx, bankmeta.num_inst, bank_data)
  audiobank.unpack_binary()

  create_xml_bank(filename, bankmeta, audiobank)

if __name__ == '__main__':
  main()
