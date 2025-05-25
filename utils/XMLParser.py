'''
### XMLParser Module

This module provides functions for parsing SEQ64-compatible XML representations of instrument bank
data used in Ocarina of Time and Majora's Mask. It converts XML elements into structured Python
dictionaries to support reconstruction and export of binary bank data.

Functions:
    `parse_abindexentry`:
        Parses the instrument bank's metadata entry.

    `parse_abbank`:
        Parses the drum list pointer, effect list pointer, and instrument list.

    `parse_drumlist`:
        Parses the drum list.

    `parse_sfxlist`:
        Parses the effect list.

    `parse_instrument`:
        Parses a single instrument structure.

    `parse_drum`:
        Parses a single drum structure.

    `parse_envelope`:
        Parses a single envelope array as a sequence of delay-argument pairs.

    `parse_sample`:
        Parses a single sample structure.

    `parse_codebook`:
        Parses a single ADPCM codebook.

    `parse_loopbook`:
        Parses a single ADPCM loopbook.

Dependencies:
    `xml.etree.ElementTree`:
        Used for navigating and extracting information from XML trees.

Intended Usage:
    This module is intended for internal use during SEQ64 XML deserialization. It serves as
    the backend for converting structured XML into valid memory representations suitable for
    bank reconstruction, modification, or binary re-export.
'''

import xml.etree.ElementTree as xml

def parse_abindexentry(element):
  struct_elem = element.find("struct")
  if struct_elem is None:
    return {}

  fields = struct_elem.findall("field")
  if len(fields) != 9:
    raise ValueError() # Metadata requires exactly 9 fields

  return {
    "address": int(fields[0].attrib["value"]),
    "size": int(fields[1].attrib["value"]),
    "medium": int(fields[2].attrib["value"]),
    "seq_player": int(fields[3].attrib["value"]),
    "table_id": int(fields[4].attrib["value"]),
    "font_id": int(fields[5].attrib["value"]),
    "num_instruments": int(fields[6].attrib["value"]),
    "num_drums": int(fields[7].attrib["value"]),
    "num_effects": int(fields[8].attrib["value"])
  }

def parse_abbank(element):
  struct_elem = element.find("struct")
  if struct_elem is None:
    return {}

  fields = struct_elem.findall("field")

  drum_pointer = int(fields[0].attrib["value"])
  sfx_pointer = int(fields[1].attrib["value"])

  instrument_elements = fields[2].findall("element")

  instrument_list = [{"index": int(elem.attrib.get("index", -1))} for elem in instrument_elements]

  return {
    "drum_pointer": drum_pointer,
    "sfx_pointer": sfx_pointer,
    "instrument_list": instrument_list
  }

def parse_drumlist(drumlist_elem):
  struct_elem = drumlist_elem.find("struct")
  fields = struct_elem.findall("field")

  drumlist = []

  for elem in fields[0].findall("element"):
    drumlist.append({"index": int(elem.attrib.get("index", -1))})

  return drumlist

def parse_sfxlist(sfxlist_elem):
  sfxlist = []

  for elem in sfxlist_elem.find("struct").findall("field")[0].findall("element"):
    struct_elem = elem.find("struct")
    fields = struct_elem.findall("field")

    sample_index = int(fields[0].attrib.get("index", -1))
    tuning = float(fields[1].attrib["value"])

    if sample_index == -1 and tuning != 0.0:
      raise ValueError()

    sfxlist.append({
      "sample": sample_index,
      "tuning": tuning
    })

  return sfxlist

def parse_instrument(item_elem):
  struct_elem = item_elem.find("struct")
  fields = struct_elem.findall("field")

  instrument = {
    "is_relocated": int(fields[0].attrib["value"]),
    "key_region_low": int(fields[1].attrib["value"]),
    "key_region_high": int(fields[2].attrib["value"]),
    "decay_index": int(fields[3].attrib["value"]),
    "envelope": int(fields[4].attrib.get('index', -1)),
    "samples": []
  }

  sample_elements = fields[5].findall("element")
  for sample in sample_elements:
    sound_struct = sample.find("struct")
    sound_fields = sound_struct.findall("field")

    sample_index = int(sound_fields[0].attrib["index"]) if "index" in sound_fields[0].attrib else -1
    tuning = float(sound_fields[1].attrib["value"])

    if sample_index == -1 and tuning != 0.0:
      raise ValueError()

    sample_data = {
      "sample": sample_index,
      "tuning": tuning
    }

    instrument["samples"].append(sample_data)

  return instrument

def parse_drum(item_elem):
  struct_elem = item_elem.find("struct")
  fields = struct_elem.findall("field")
  sound_struct = fields[4].find("struct")
  sound_fields = sound_struct.findall("field")

  if len(fields) != 6:
    raise ValueError() # ROM Description is outdated

  assert int(fields[3].attrib["value"]) == 0, "" # Padding byte is always 0

  sample_index = int(sound_fields[0].attrib["index"]) if "index" in sound_fields[0].attrib else -1
  tuning = float(sound_fields[1].attrib["value"])

  if sample_index == -1 and tuning != 0.0:
      raise ValueError() # nullptr sample tuning values should be 0.0

  drum = {
    "decay_index": int(fields[0].attrib["value"]),
    "pan": int(fields[1].attrib["value"]),
    "is_relocated": int(fields[2].attrib["value"]),
    "padding": 0,
    "sample": {
      "sample": sample_index,
      "tuning": tuning
    },
    "envelope": int(fields[5].attrib.get('index', -1))
  }

  return drum

def parse_envelope(item_elem):
  struct_elem = item_elem.find('struct')
  fields = struct_elem.findall("field")

  if len(fields) % 2 != 0:
    raise ValueError() # Uneven number of points

  points = []
  for i in range(0, len(fields), 2):
    delay = int(fields[i].attrib["value"])
    arg = int(fields[i + 1].attrib["value"])
    points.append({"delay": delay, "arg": arg})

  return {"points": points}

def parse_sample(item_elem):
  struct_elem = item_elem.find("struct")
  fields = struct_elem.findall("field")

  if len(fields) != 4:
    raise ValueError() # ROM Description is outdated

  bitfield = int(fields[0].attrib["value"])

  unk_0        = (bitfield >> 31) & 0b1
  codec        = (bitfield >> 28) & 0b111
  medium       = (bitfield >> 26) & 0xb11
  is_cached    = (bitfield >> 25) & 1
  is_relocated = (bitfield >> 24) & 1
  size         = (bitfield >> 0) & 0b111111111111111111111111

  loop_index = int(fields[2].attrib["index"]) if "index" in fields[2].attrib else -1
  book_index = int(fields[3].attrib["index"]) if "index" in fields[2].attrib else -1

  assert loop_index  != -1
  assert book_index  != -1
  assert codec in (0, 3)
  assert medium == 0
  assert is_relocated == 0

  sample = {
    "unk_0": unk_0,
    "codec": codec,
    "medium": medium,
    "is_cached": is_cached,
    "is_relocated": is_relocated,
    "size": size,
    "sample_pointer": int(fields[1].attrib["value"]),
    "loop": loop_index,
    "book": book_index
  }

  return sample

def parse_codebook(item_elem):
  struct_elem = item_elem.find("struct")
  fields = struct_elem.findall("field")

  order = int(fields[0].attrib["value"])
  num_predictors = int(fields[1].attrib["value"])

  predictors_elem = fields[2].findall("element")

  if len(predictors_elem) != num_predictors:
    raise ValueError() # Number of arrays is the num_pred value

  predictors = []
  for array in predictors_elem:
    data_field = array.find("struct").find("field")
    data_values = [int(el.attrib["value"]) for el in data_field.findall("element")]

    if len(data_values) != 16:
      raise ValueError() # Not enough predictor coefficients

    predictors.append(data_values)

  book = {
    "order": order,
    "num_predictors": num_predictors,
    "predictor_arrays": predictors
  }

  return book

def parse_loopbook(item_elem):
  struct_elem = item_elem.find("struct")
  fields = struct_elem.findall("field")

  loop_start = int(fields[0].attrib["value"])
  loop_end = int(fields[1].attrib["value"])
  loop_count = int(fields[2].attrib["value"])
  num_samples = int(fields[3].attrib["value"])

  has_tail = struct_elem.attrib.get("HAS_TAIL", "0") == "1"
  tail_data = None

  if has_tail:
    predictors_elem = fields[4].find("element")
    if predictors_elem is None:
      raise ValueError() # Should have tail data

    data_field = predictors_elem.find("struct").find("field")
    tail_data = [int(el.attrib["value"]) for el in data_field.findall("element")]

    if len(tail_data) != 16:
      raise ValueError() # Not enough predictor coefficients

  return {
    "loop_start": loop_start,
    "loop_end": loop_end,
    "loop_count": loop_count,
    "num_samples": num_samples,
    "predictor_array": tail_data
  }

if __name__ == '__main__':
  pass
