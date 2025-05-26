# Zelda64 Instrument Bank Converter
This is a WIP rewrite of a binary to XML to binary script that converts Zelda64 instrument banks from binary to SEQ64-compatible XML and vice versa. The rewrite aims to improve code, and to allow others to easily use or modify it.

## What it Does
This code takes a binary bank and bankmeta file for the Nintendo 64 Zelda games and turns it into a SEQ64 XML file, and vice versa.

## 🔧 How to Use
> 1. Place the following files and folders into the same directory:
>    - `📄 bin_to_xml_rewrite.py` — the main script.
>    - `📁/utils` — the utility package that contains necessary modules.
> 2. Run the script from a terminal using the required arguments with the required input files.

### ⌨️ Command-Line Usage
```
python <script_name.py> [-h] -g {oot, mm} <input_file> [input_file ...]
```

#### 📥 Terminal Arguments
| Argument | Description |
| --- | --- |
| `-h` | Displays the help message in the terminal. |
| `files` | The SEQ64-compatible XML file or `.zbank` and `.bankmeta` file pair. |
| `-g {oot, mm}` | Specifies which game's sample and envelope names are output for XML. |

> [!CAUTION]
> If your script or file names contain spaces, they must be enclosed in quotes.

> [!TIP]
> You can drag and drop files onto the terminal window to automatically insert their paths (enclosed in quotes).

### ❓ Terminal Help Message
The output of the help message is below:
```
usage: [>_] python bin_to_xml_rewrite.py [-h] file [files ...] -g {oot, mm}

This script converts Zelda64 instrument banks between binary and SEQ64-compatible XML.

positional arguments:
  files                a SEQ64-compatible XML file or a pair of binary files (.zbank and .bankmeta)

options:
  -h, --help           show this help message and exit
  -g, --game {oot,mm}  specifies which game's sample and envelope names the converter will use for XML files
```

## To-Do
- [x] Parse binary instrument bank and all of its information
- [x] Store unpacked binary data into XML-ready dictionaries
- [x] Write out the XML-ready data into a SEQ64 XML file
- [x] Add functionality to repack a SEQ64 XML instrument bank into a binary instrument bank and bankmeta file
- [x] Add proper argument parsing
- [x] Add docstrings
- [x] Add vanilla names for instruments and samples for both games
- [ ] Add sound effect packing for xml to binary
- [ ] Prettify CLI output
- [x] Add parsing YAML to binary
- [ ] Add parsing binary to YAML

## Required XML Audiobank Structure
> [!CAUTION]
> If your ROM description does not have the following `<abfstructs>` layout, then XML to binary will not work:
```xml
<!-- Beginning of audiobank file structure -->
  <abfstructs align="16">
    <!-- ABIndex Struct -->
    <struct name="ABIndex">
      <field name="NUM_BANK" datatype="uint16" ispointer="0" isarray="0" meaning="NUM_BANK"/>
      <field name="Padding Bytes" datatype="uint16" ispointer="0" isarray="1" meaning="None"
             arraylenfixed="7" defaultval="0"/>
      <field name="Bank List" datatype="ABIndexEntry" ispointer="0" isarray="1"
             meaning="List of Banks" arraylenvar="NUM_BANK"/>
    </struct>
    <!-- ABIndexEntry Struct -->
    <struct name="ABIndexEntry">
      <field name="Bank Offset in Audiobank" datatype="uint32" ispointer="1" isarray="0" meaning="Ptr Bank (in Audiobank)"
             ptrto="ABHeader"/>
      <field name="Bank Size" datatype="uint32" ispointer="0" isarray="0" meaning="Bank Length"/>
      <field name="Sample Medium" datatype="uint8" ispointer="0" isarray="0" meaning="None"
             defaultval="2"/>
      <field name="Sequence Player" datatype="uint8" ispointer="0" isarray="0" meaning="None"
             defaultval="2"/>
      <field name="Audiotable ID" datatype="uint8" ispointer="0" isarray="0" meaning="Sample Table number"/>
      <field name="Soundfont ID" datatype="uint8" ispointer="0" isarray="0" meaning="None"
             defaultval="255"/>
      <field name="NUM_INST" datatype="uint8" ispointer="0" isarray="0" meaning="NUM_INST"/>
      <field name="NUM_DRUM" datatype="uint8" ispointer="0" isarray="0" meaning="NUM_DRUM"/>
      <field name="NUM_SFX" datatype="uint16" ispointer="0" isarray="0" meaning="NUM_SFX"/>
    </struct>
    <struct name="ABHeader"/>
    <struct name="ABBank">
      <field name="Drum List Pointer" datatype="uint32" ispointer="1" isarray="0" meaning="Ptr Drum List"
             ptrto="ABDrumList"/>
      <field name="Effect List Pointer" datatype="uint32" ispointer="1" isarray="0" meaning="Ptr SFX List"
             ptrto="ABSFXList"/>
      <field name="Instrument List" datatype="uint32" ispointer="1" isarray="1" meaning="List of Ptrs to Insts"
             ptrto="ABInstrument" arraylenvar="NUM_INST"/>
    </struct>
    <struct name="ABDrumList">
      <field name="Drum List" datatype="uint32" ispointer="1" isarray="1" meaning="List of Ptrs to Drums"
             ptrto="ABDrum" arraylenvar="NUM_DRUM"/>
    </struct>
    <struct name="ABSFXList">
      <field name="Effect List" datatype="ABSound" ispointer="0" isarray="1" meaning="List of Sounds"
             arraylenvar="NUM_SFX"/>
    </struct>
    <struct name="ABInstrument">
      <field name="Relocated (Bool)" datatype="uint8" ispointer="0" isarray="0" meaning="None"/>
      <field name="Key Region Low (Max range)" datatype="uint8" ispointer="0" isarray="0"
             meaning="Split Point 1"/>
      <field name="Key Region High (Min range)" datatype="uint8" ispointer="0" isarray="0"
             meaning="Split Point 2"/>
      <field name="Decay Index" datatype="uint8" ispointer="0" isarray="0"
             meaning="None"/>
      <field name="Envelope Pointer" datatype="uint32" ispointer="1" isarray="0"
             meaning="Ptr Envelope" ptrto="ABEnvelope"/>
      <field name="Sample Pointer Array" datatype="ABSound" ispointer="0"
             isarray="1" meaning="List of 3 Sounds for Splits" arraylenfixed="3"/>
    </struct>
    <struct name="ABDrum">
      <field name="Decay Index" datatype="uint8" ispointer="0" isarray="0"
             meaning="None"/>
      <field name="Pan" datatype="uint8" ispointer="0" isarray="0" meaning="None"/>
      <field name="Relocated (Bool)" datatype="uint8" ispointer="0" isarray="0"
             meaning="None"/>
      <field name="Padding Byte" datatype="uint8" ispointer="0" isarray="0"
             meaning="None"/>
      <field name="Drum Sound" datatype="ABSound" ispointer="0" isarray="0"
             meaning="Drum Sound"/>
      <field name="Envelope Pointer" datatype="uint32" ispointer="1" isarray="0"
             meaning="Ptr Envelope" ptrto="ABEnvelope"/>
    </struct>
    <struct name="ABSound">
      <field name="Sample Pointer" datatype="uint32" ispointer="1" isarray="0"
             meaning="Ptr Sample" ptrto="ABSample"/>
      <field name="Tuning" datatype="float32" ispointer="0" isarray="0" meaning="None"/>
    </struct>
    <struct name="ABEnvelope">
      <field name="Time or Opcode 1" datatype="int16" ispointer="0" isarray="0" meaning="none"/>
      <field name="Amp or Arg 1" datatype="int16" ispointer="0" isarray="0" meaning="none"/>
      <field name="Time or Opcode 2" datatype="int16" ispointer="0" isarray="0" meaning="none"/>
      <field name="Amp or Arg 2" datatype="int16" ispointer="0" isarray="0" meaning="none"/>
      <field name="Time or Opcode 3" datatype="int16" ispointer="0" isarray="0" meaning="none"/>
      <field name="Amp or Arg 3" datatype="int16" ispointer="0" isarray="0" meaning="none"/>
      <field name="Time or Opcode 4" datatype="int16" ispointer="0" isarray="0" meaning="none"/>
      <field name="Amp or Arg 4" datatype="int16" ispointer="0" isarray="0" meaning="none"/>
    </struct>
    <struct name="ABSample">
      <!-- Bitfield: uint8, uint8, and uint16 (meaning Sample Length) originally -->
      <field name="Bitfield" datatype="uint32" ispointer="0"
             isarray="0" meaning="None"/>
      <field name="Sample Offset in Audiotable" datatype="uint32" ispointer="0" isarray="0"
             meaning="Sample Address (in Sample Table)" ptrto="ATSample"/>
      <field name="Loop Pointer" datatype="uint32" ispointer="1" isarray="0"
             meaning="Ptr ALADPCMLoop" ptrto="ALADPCMLoop"/>
      <field name="Book Pointer" datatype="uint32" ispointer="1" isarray="0"
             meaning="Ptr ALADPCMBook" ptrto="ALADPCMBook"/>
    </struct>
    <struct name="ALADPCMBook" NUM_PRED="-1">
      <field name="Order" datatype="int32" ispointer="0" isarray="0" meaning="None"/>
      <field name="Number of Predictors" datatype="int32" ispointer="0" isarray="0"
             meaning="NUM_PRED"/>
      <field name="Codebook" datatype="ALADPCMPredictor" ispointer="0" isarray="1"
             meaning="Array of Predictors" arraylenvar="NUM_PRED"/>
    </struct>
    <struct name="ALADPCMPredictor">
      <field name="data" datatype="int16" ispointer="0" isarray="1" meaning="None"
             arraylenfixed="16"/>
    </struct>
    <struct name="ALADPCMLoop" HAS_TAIL="-1">
      <field name="Loop Start" datatype="uint32" ispointer="0" isarray="0"
             meaning="Loop Start"/>
      <field name="Loop End (Sample Length if Count = 0)" datatype="uint32" ispointer="0"
             isarray="0" meaning="Loop End"/>
      <field name="Loop Count" datatype="int32" ispointer="0" isarray="0"
             meaning="Loop Count" defaultval="-1"/>
      <field name="Number of Samples" datatype="uint32" ispointer="0" isarray="0"
             meaning="None" defaultval="0"/>
      <field name="Loopbook" datatype="ALADPCMTail" ispointer="0" isarray="1"
             meaning="Tail Data (if Loop Start != 0)" arraylenvar="HAS_TAIL"/>
    </struct>
    <struct name="ALADPCMTail">
      <field name="data" datatype="int16" ispointer="0" isarray="1"
             meaning="None" arraylenfixed="16"/>
    </struct>
  </abfstructs>
  <!-- End of audiobank file structure -->
```
