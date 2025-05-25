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

# To-Do
- [x] Parse binary instrument bank and all of its information
- [x] Store unpacked binary data into XML-ready dictionaries
- [x] Write out the XML-ready data into a SEQ64 XML file
- [x] Add functionality to repack a SEQ64 XML instrument bank into a binary instrument bank and bankmeta file
- [x] Add proper argument parsing
- [x] Add docstrings
- [x] Add vanilla names for instruments and samples for both games
- [ ] Add sound effect packing for xml to binary
- [ ] Prettify CLI output
