# Zelda64 Binary to XML to Binary Instrument Bank
This is a WIP rewrite of a binary to XML to binary script that converts Zelda64 instrument banks from binary to SEQ64-compatible XML and vice versa. The rewrite aims to improve code, and to allow others to easily use or modify it.

## What it Does
This code takes a binary bank and bankmeta file for the Nintendo 64 Zelda games and turns it into a SEQ64 XML file, and vice versa.

### To-Do
- [x] Parse binary instrument bank and all of its information
- [x] Store unpacked binary data into XML-ready dictionaries
- [x] Write out the XML-ready data into a SEQ64 XML file
- [x] Add functionality to repack a SEQ64 XML instrument bank into a binary instrument bank and bankmeta file
- [x] Add proper argument parsing
- [x] Add docstrings
- [ ] Add vanilla names for instruments and samples for both games
- [ ] Prettify CLI output
