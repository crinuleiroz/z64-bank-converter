'''
### Utils Package

This package contains utility modules that support the parsing, manipulation, and serialization
of instrument banks for Ocarina of Time and Majora's Mask.

Modules:
    `Enums`:
        Defines enumeration classes used throughout the instrument bank processing for clarity and type safety.

    `Helpers`:
        Provides low-level helper functions for data alignment, padding, bit manipulation, and binary operations.

    `XMLParser`:
        Implements functionality to parse instrument bank data from SEQ64-compatible XML.

    `audiobank.Audiobank`:
        Core class representing an entire instrument bank, including metadata and references
        to all constituent components such as instruments, drums, sound effects, samples,
        envelopes, and ADPCM loopbooks and codebooks.

    `audiobank.structs.Instrument`:
        Defines the `Instrument` class representing an individual instrument, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `audiobank.structs.Drum`:
        Defines the `Drum` class representing an individual drum, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `audiobank.structs.Effect`:
        Defines the `SoundEffect` class for representing an individual sound effect, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `audiobank.structs.Envelope`:
        Defines the `Envelope` class representing an individual envelope array, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `audiobank.structs.Sample`:
        Defines the `Sample` class representing an individual audio sample, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `audiobank.structs.Loopbook`:
        Defines the `AdpcmLoop` class representing an ADPCM loop structure, with methods
        for binary parsing and serialization.

    `audiobank.structs.Codebook`:
        Defines the `AdpcmBook` class representing an ADPCM codebook, with methods
        for binary parsing and serialization.


Functionality:
    - Parse and serialize instrument bank binary data to XML and vice versa.
    - Provide reusable enums and helper utilities for consistent data handling.
    - Support detailed structure representations of instrument bank components.
    - Facilitate packing and unpacking of instrument bank data.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `xml.etree.ElementTree`:
        For XML parsing and serialization.

    `itertools`:
        Used in specific modules (e.g., Codebook) for efficient data unpacking.

    `enum`:
        Used in `Enum` for enumeration typing.

Intended Usage:
    This package is intended to provide a comprehensive toolkit for converting Ocarina of Time
    and Majora's Mask instrument banks between binary formats and SEQ64-compatible XML.
'''
