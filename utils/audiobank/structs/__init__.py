'''
### Structs Package

This package provides class definitions and associated parsing, serialization,
and data manipulation methods for the fundamental data structures used in
Ocarina of Time and Majora's Mask instrument banks.

Modules:
    `Instrument`:
        Defines the `Instrument` class representing an individual instrument, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `Drum`:
        Defines the `Drum` class representing an individual drum, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `Effect`:
        Defines the `SoundEffect` class for representing an individual effect, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `Envelope`:
        Defines the `Envelope` class representing an individual envelope array, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `Sample`:
        Defines the `Sample` class representing an individual instrument bank sample, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `Loopbook`:
        Defines the `AdpcmLoop` class representing an individual ADPCM loopbook, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `Codebook`:
        Defines the `AdpcmBook` class representing an individual ADPCM codebook, with methods
        for binary parsing, serialization, and XML dictionary conversion.

Functionality:
    - Parse structures from raw binary data (`from_bytes`).
    - Serialize objects back to binary format (`to_bytes`).
    - Convert structures to nested dictionary formats suitable for XML export (`to_dict`).
    - Validate data consistency during parsing and manipulation.
    - Maintain relationships between linked data such as samples, envelopes, and codebooks.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `itertools`:
        Used in specific modules (e.g., Codebook) for efficient data unpacking.

    `Enums`:
        For representing codec, medium, and XML tag identifiers.

    `Helpers`:
        For alignment, padding, and low-level binary operations.

Intended Usage:
    This package supports the unpacking and repacking of instrument bank data
    from binary Ocarina of Time and Majora's Mask formats into SEQ64-compatible
    XML and vice versa. Used in conjunction with 'Audiobank' and 'Bankmeta' for
    full instrument bank conversion.
'''
