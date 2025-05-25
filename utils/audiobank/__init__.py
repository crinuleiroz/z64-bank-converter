'''
### Audiobank Package

This package defines high-level classes and structures for representing, parsing, modifying,
and exporting full instrument banks from Ocarina of Time and Majora's Mask.

Modules:
    `Audiobank`:
        Core class representing an entire instrument bank, including metadata and references
        to all constituent components such as instruments, drums, sound effects, samples,
        envelopes, and ADPCM loopbooks and codebooks.

    `structs.Instrument`:
        Defines the `Instrument` class representing an individual instrument, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `structs.Drum`:
        Defines the `Drum` class representing an individual drum, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `structs.Effect`:
        Defines the `SoundEffect` class for representing an individual sound effect, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `structs.Envelope`:
        Defines the `Envelope` class representing an individual envelope array, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `structs.Sample`:
        Defines the `Sample` class representing an individual audio sample, with methods
        for binary parsing, serialization, and XML dictionary conversion.

    `structs.Loopbook`:
        Defines the `AdpcmLoop` class representing an ADPCM loop structure, with methods
        for binary parsing and serialization.

    `structs.Codebook`:
        Defines the `AdpcmBook` class representing an ADPCM codebook, with methods
        for binary parsing and serialization.

Functionality:
    - Load an entire instrument bank from binary data (`from_bytes`) or XML (`from_dict`).
    - Export bank data back to binary format (`to_bytes`) or XML dictionaries (`to_dict`).
    - Manage internal registries for reusing and referencing shared data structures such as
      samples, envelopes, and ADPCM predictors.
    - Maintain pointer relationships between structures to ensure binary integrity.
    - Validate data consistency and resolve references during parsing and serialization.

Dependencies:
    `struct`:
        For low-level binary packing and unpacking operations.

    `Enums`:
        For representing codec, medium, and XML tag identifiers.

    `Helpers`:
        Provides binary utilities for padding, alignment, and integer manipulation.

    `XMLParser`:
        For converting XML trees into instrument bank structures.

Intended Usage:
    The `audiobank` package is the core for converting instrument bank data
    between raw binary and SEQ64-compatible XML formats.
'''
