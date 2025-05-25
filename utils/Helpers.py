'''
### Helpers Module

This module provides low-level utility functions to assist with binary data manipulation
and alignment, commonly used throughout the instrument bank parsing and serialization process.

Functions:
    `align_to_16`:
        Rounds the given integer up to the next multiple of 16.

    `add_padding_to_16`:
        Adds zero-bytes padding to a byte sequence so its length is a multiple of 16.

Dependencies:
    `struct`:
        Imported and exposed for byte-level packing and unpacking operations needed by other modules.

Intended Usage:
    This module is intended to be imported whenever binary data alignment or padding is required,
    ensuring consistency and correctness when reading or writing binary instrument bank files.
    It also exposes the standard `struct` module for convenient binary data handling.
'''

# Import struct as it is used by /audiobank
import struct as _struct

''' Helper Functions '''
def align_to_16(data: int) -> int:
  return (data + 0x0F) & ~0x0F # or (size + 0xF) // 0x10 * 0x10

def add_padding_to_16(packed_data: bytearray) -> bytearray:
  padding: int = (-len(packed_data)) & 0x0F # or (0x10 - (size % 0x10)) % 0x10
  return packed_data + b'\x00' * padding

# Explose struct
struct = _struct

if __name__ == '__main__':
  pass
