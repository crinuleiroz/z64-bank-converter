''' A script for converting Zelda64 instrument banks between their binary format, the SEQ64-compatible XML format, and a similar YAML format '''

# Define current version
CURRENT_VERSION = '2025.05.26'

# Imports
import os
import sys
import argparse
import datetime
from typing import Final
from dataclasses import dataclass, field
import xml.etree.ElementTree as xml

# Ensure /utils is present and can be imported
try:
  import utils

  # Import the Bankmeta and Audiobank
  from utils.audiobank.Audiobank import Bankmeta, Audiobank

  # Import the XML Tag enum
  from utils.Enums import XMLTags

  # Import sample names
  from utils.SampleNames import OOT_SAMPLE_NAMES, MM_SAMPLE_NAMES
  import utils.audiobank.structs.Sample as sample_struct

  from utils.YAMLSerializer import *

except ImportError as e:
  print("Error: One or more required utilities are missing.")
  print(f"Details: {e}")
  print("\nPlease ensure the 'utils' package is correcty installed and all its dependencies are available.")
  input("\nPress Enter to exit...")
  sys.exit(1)

# Create ANSI formatting for terminal messages
# ANSI COLORS: https://talyian.github.io/ansicolors/
# TERMINAL TEXT COLORS
RED        : Final = '\x1b[31m'
PINK_218   : Final = '\x1b[38;5;218m'
PINK_204   : Final = '\x1b[38;5;204m'
YELLOW     : Final = '\x1b[33m'
YELLOW_229 : Final = '\x1b[38;5;229m'
CYAN       : Final = '\x1b[36m'
BLUE_39    : Final = '\x1b[38;5;39m'
GRAY_245   : Final = '\x1b[38;5;245m'
GRAY_248   : Final = '\x1b[38;5;248m'
GREEN_79   : Final = '\x1b[38;5;79m'

# TERMINAL TEXT STYLES
BOLD      : Final = '\x1b[1m'
ITALIC    : Final = '\x1b[3m'
UNDERLINE : Final = '\x1b[4m'
STRIKE    : Final = '\x1b[9m'
RESET     : Final = '\x1b[0m' # Resets all text styles and colors

# TERMINAL CLEANERS
PL  : Final = '\x1b[F' # Move cursor to previous line
CL  : Final = '\x1b[K' # Clear line

# Argument Parser
def parse_args():
  parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    usage=f'{GRAY_248}[>_]{RESET} {YELLOW_229}python{RESET} {BLUE_39}{os.path.basename(sys.argv[0])}{RESET} {GRAY_245}[-h]{RESET} {BLUE_39}file [files ...]{RESET} {GRAY_245}-g {{oot, mm}}{RESET}',
    description='''This script converts Zelda64 instrument banks between binary and SEQ64-compatible XML.'''
  )

  parser.add_argument(
    'files',
    nargs='+',
    help="a SEQ64-compatible XML file or a pair of binary files (.zbank and .bankmeta)"
  )
  parser.add_argument(
    '-g',
    '--game',
    choices=['oot', 'mm'],
    required=True,
    help="specifies which game's sample and envelope names the converter will use for XML files"
  )
  parser.add_argument(
    '-o',
    '--output',
    choices=['xml', 'yaml'],
    required=False,
    help="specifies the output type when converting from binary files (defaults to xml)"
  )

  return parser.parse_args()

# Create date for the XML and filename
DATE = datetime.datetime.now().replace(microsecond=0).isoformat(' ')
DATE_FILENAME = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

''' Classes '''
@dataclass
class XMLDataEntry:
  enum_tag: XMLTags
  xml_tag: str
  xml_list: list[dict] = field(default_factory=list)
  audiobank: object = None  # audiobank is passed in during initialization

  def __post_init__(self):
    self.parent_tag = self.enum_tag.value

    self._populate_xml_list()

  def _populate_xml_list(self):
    if self.xml_list is None:
      self.xml_list = []

  def get_address(self) -> str:
    address_map = {
      XMLTags.ABDRUMLIST: ("drumlist_offset", "num_drums"),
      XMLTags.ABSFXLIST:  ("sfxlist_offset", "num_effects")
    }

    if self.enum_tag in address_map:
      list_attr, num_attr = address_map[self.enum_tag]
      list_value = getattr(self.audiobank, list_attr, 0)
      if list_value != 0 and getattr(self.audiobank.bankmeta, num_attr, 0) != 0:
        return str(list_value)
    return ''

''' XML Writing Functions '''
def dict_to_xml(tag: str, d, parent: xml.Element = None) -> xml.Element:
    ''' Convert nested dictionary to XML '''
    # Ensure we're working with a dictionary or string for the current item
    if isinstance(d, dict):
      element = xml.Element(tag)

      for key, value in d.items():
        # Create a comment if the key is "__comment__"
        if key == "__comment__":
          element.append(xml.Comment(value))

        # Recursion if the value is a dict
        elif isinstance(value, dict):
          dict_to_xml(key, value, element)

        # Create multiple separate elements for each list entry
        elif isinstance(value, list):
          for item in value:
            # The items should be dictionaries, so more recursion
            if isinstance(item, dict):
              child = dict_to_xml(key, item)
              element.append(child)

        else:
          element.set(key, str(value) if value is not None else "")

    else:
      # If it's a string, just add it as the text content
      element = xml.Element(tag)
      element.text = str(d) if d is not None else ""

    # Add each separate item to the parent element
    # e.g. prevents multiple <instruments> tags for each instrument <item> tag
    if parent is not None:
      parent.append(element)

    return element

def create_xml_bank(filename: str, bankmeta: Bankmeta, audiobank: Audiobank, game: str) -> None:
  ''' Build XML file '''
  xml_root = xml.Element('bank')

  for key, value in bankmeta.attributes.items():
    xml_root.set(key, str(value))

  xml_tree = xml.ElementTree(xml_root)
  if game == 'oot':
    xml_comment = xml.Comment(f'\n      ORIGIN GAME: OCARINA OF TIME\n      DATE CREATED: {DATE}\n\n      This bank was created from a binary bank file, because of this there may be errors or differences from the original bank!\n  ')
  elif game == 'mm':
    xml_comment = xml.Comment(f'\n      ORIGIN GAME: MAJORAS MASK\n      DATE CREATED: {DATE}\n\n      This bank was created from a binary bank file, because of this there may be errors or differences from the original bank!\n  ')
  else:
    xml_comment = xml.Comment(f'\n      DATE CREATED: {DATE}\n\n      This bank was created from a binary bank file, because of this there may be errors or differences from the original bank!\n  ')

  xml_data = [
    XMLDataEntry(XMLTags.ABINDEXENTRY, 'struct', [bankmeta.to_dict()]),
    XMLDataEntry(XMLTags.ABHEADER,     'struct', [{"name": 'ABHeader'}])
  ]

  audiobank_xml_data = audiobank.to_xml()

  xml_data.extend([
    XMLDataEntry(XMLTags.ABBANK,       'struct', audiobank_xml_data['abbank']),
    XMLDataEntry(XMLTags.ABDRUMLIST,   'struct', audiobank_xml_data['abdrumlist'], audiobank),
    XMLDataEntry(XMLTags.ABSFXLIST,    'struct', audiobank_xml_data['absfxlist'], audiobank),
    XMLDataEntry(XMLTags.INSTRUMENTS,  'item',   audiobank_xml_data['instruments']),
    XMLDataEntry(XMLTags.DRUMS,        'item',   audiobank_xml_data['drums']),
    XMLDataEntry(XMLTags.ENVELOPES,    'item',   audiobank_xml_data['envelopes']),
    XMLDataEntry(XMLTags.SAMPLES,      'item',   audiobank_xml_data['samples']),
    XMLDataEntry(XMLTags.ALADPCMBOOKS, 'item',   audiobank_xml_data['aladpcmbooks']),
    XMLDataEntry(XMLTags.ALADPCMLOOPS, 'item',   audiobank_xml_data['aladpcmloops'])
  ])

  for entry in xml_data:
    element = xml.Element(entry.parent_tag)

    address = entry.get_address()
    if address:
      element.set("address", address)

    if entry.xml_list:
      for item in entry.xml_list:
        dict_to_xml(entry.xml_tag, item, element)

    xml_root.append(element)

  with open(f'BANK_{filename}_{DATE_FILENAME}.xml', 'wb') as f:
    xml.indent(xml_tree)
    f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write(xml.tostring(xml_comment) + b'\n')
    xml_tree.write(f, encoding='utf-8', xml_declaration=False)

''' Yaml Writing Functions '''
def create_yaml_bank(filename: str, bankmeta: Bankmeta, audiobank: Audiobank):
  output_yaml = {
    "bankmeta": bankmeta.to_yaml(),
    "bank": audiobank.to_yaml()
  }

  with open(f'BANK_{filename}_{DATE_FILENAME}.yaml', 'w') as f:
    yaml.dump(output_yaml, f, sort_keys=False)

''' Binary Writing Functions '''
def create_binary_bank(filename: str, bankmeta: Bankmeta, audiobank: Audiobank) -> None:
  bankmeta_bytes = bankmeta.to_bytes()
  bank_bytes = audiobank.to_bytes()

  with open(f'{filename}_{DATE_FILENAME}.bankmeta', 'wb') as bankmeta:
    bankmeta.write(bankmeta_bytes)

  with open(f'{filename}_{DATE_FILENAME}.zbank', 'wb') as bank:
    bank.write(bank_bytes)

''' Helper Functions '''
def read_binary(filename: str) -> bytearray:
  with open(filename, 'rb') as file:
    binary = bytearray(file.read())
  return binary

def get_nested_attr(obj, attr_chain):
  for attr in attr_chain.split('.'):
    obj = getattr(obj, attr)
  return obj

''' Main Function '''
def main() -> None:
  args = parse_args()
  files = args.files
  game = args.game
  out_type = args.output

  if len(files) == 1:
    [file] = files
    if file.lower().endswith('.xml'):
      mode = 'xml'
    elif file.lower().endswith('.yaml') or file.lower().endswith('.yml'):
      mode = 'yaml'
    else:
      print("Error: A single input files must be an XML or YAML file.")
      sys.exit(1)

  elif len(files) == 2:
    file1, file2 = files
    ext1, ext2 = os.path.splitext(file1)[1].lower(), os.path.splitext(file2)[1].lower()
    extensions: set = {ext1, ext2}

    if extensions != {'.zbank', '.bankmeta'}:
      print("Error: For binary mode, you must supply both a .bankmeta and .zbank file.")
      sys.exit(1)
    mode = 'binary'

    bankmeta_file = file1 if file1.lower().endswith('.bankmeta') else file2
    bank_file     = file1 if file1.lower().endswith('.zbank') else file2

  filename = os.path.basename(os.path.splitext(files[0])[0])

  # Determine which game's sample names to use
  if game == 'oot':
    sample_struct.SAMPLE_NAMES.update(OOT_SAMPLE_NAMES)
  elif game == 'mm':
    sample_struct.SAMPLE_NAMES.update(MM_SAMPLE_NAMES)

  if mode == 'xml':
    ''' From XML '''
    tree = xml.parse(files[0])
    bank_element = tree.getroot()

    # Create the binary bank and bankmeta
    bankmeta = Bankmeta.from_xml(bank_element) # Instantiate the bankmeta and collect all its data

    # Required for audiotable offset shenanigans
    sample_struct.AUDIOTABLE_ID = bankmeta.table_id
    sample_struct.DETECTED_GAME = game

    audiobank = Audiobank.from_xml(bankmeta, bank_element) # Instantiate the audiobank and collect all its data
    create_binary_bank(filename, bankmeta, audiobank)

  if mode == 'yaml':
    with open(file, 'r') as f:
      data = yaml.safe_load(f)

    bankmeta_dict = data.get('bankmeta')
    bank_dict = data.get('bank')

    if not bankmeta_dict or not bank_dict:
      raise Exception() # Empty dictionaries

    bankmeta = Bankmeta.from_yaml(bankmeta_dict)
    audiobank = Audiobank.from_yaml(bankmeta, bank_dict)

    create_binary_bank(filename, bankmeta, audiobank)

  elif mode == 'binary':
    ''' From binary zbank and bankmeta '''
    bankmeta_data = read_binary(bankmeta_file)
    bank_data = read_binary(bank_file)

    # Create the XML bank
    bankmeta = Bankmeta.from_bytes(bankmeta_data) # Instantiate the bankmeta and collect all its data

    # Required for audiotable offset shenanigans
    sample_struct.AUDIOTABLE_ID = bankmeta.table_id
    sample_struct.DETECTED_GAME = game

    audiobank = Audiobank.from_bytes(bankmeta, bank_data) # Instantiate the audiobank and collect all its data

    if out_type == 'yaml':
      create_yaml_bank(filename, bankmeta, audiobank)
    else:
      create_xml_bank(filename, bankmeta, audiobank, game)

if __name__ == '__main__':
  main()
