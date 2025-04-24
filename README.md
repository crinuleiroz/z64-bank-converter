# Zelda64 Binary Instrument Bank to SEQ64 XML Instrument Bank
This is a WIP rewrite of a bin to xml script that converts binary banks to xml banks. The rewrite aims to improve code, and to allow others to easily use or modify it.

## What it Does
This code takes a binary bank and bankmeta file for the Nintendo 64 Zelda games and turns it into a SEQ64 XML file, and eventually vice versa.

Ctypes is used to recreate the structures as they are found in ZeldaRET's decompilations of [Ocarina of Time](https://github.com/zeldaret/oot) and [Majora's Mask](https://github.com/zeldaret/mm). Struct is used to unpack and pack the data into big endian format as ctypes uses the system format (generally little endian).

### To-Do
- [x] Parse binary instrument bank and all of its information using ctypes and struct
- [x] Store unpacked binary data into XML-ready dictionaries
- [x] Write out the XML-ready data into a SEQ64 XML file
- [ ] Add functionality to repack a SEQ64 XML instrument bank into a binary instrument bank and bankmeta file
- [ ] Add proper argument parsing
- [ ] Add docstrings
- [ ] Add vanilla names for instruments and samples for both games
