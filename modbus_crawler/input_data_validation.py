from typing import Optional
import re

# allowed column names in csv file or pandas data frame.
# Noie: any input names will be stripped, lower cased and '_' removed to be robust against typos of user inputs
csv_column_names: list[str] = ['registerstart', 'registerend', 'name', 'registertype', 'datatype', 'unit', 'scaling',
                               'unitid', 'description']

# List of possible data types:
data_types = (('int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64', 'float16', 'float32', 'float64', 'bool')
              + tuple(f'string{i}' for i in range(129)))

# List of aliases for data types
# Note: any input names will be lower cased to be robust against typos of user inputs
# Note: as a modbus register is 16 bit long, we use the term 'int' for a 16 bit variable
data_type_lookup: dict[str, str] = {
    'int': 'int16', 'short': 'int16', 'int16': 'int16',
    'uint': 'uint16', 'ushort': 'uint16', 'uint16': 'uint16',
    'dint': 'int32', 'long': 'int32', 'int32': 'int32',
    'ulong': 'uint32', 'uint32': 'uint32',
    'int64': 'int64',
    'uint64': 'uint64',
    'half': 'float16', 'float16': 'float16',
    'float': 'float32', 'single': 'float32', 'real': 'float32', 'float32': 'float32',
    'double': 'float64', 'float64': 'float64',
    'bool': 'bool', 'bit': 'bool', 'boolean': 'bool', 'coil': 'bool',
    **{f'string{i}': f'string{i}' for i in range(129)}
}

# List of possible register types
register_types = ('i', 'h', 'c', 'd')
# List of aliases for register types.
# Note: any input names will be lower cased to be robust against typos of user inputs
register_type_lookup: dict[str, str] = {
    'i': 'i', '4': 'i', '0x04': 'i', 'ir': 'i', 'inputregister': 'i', 'inputreg': 'i',
    'h': 'h', '3': 'h', '0x03': 'h', 'hr': 'h', 'holdingregister': 'h', 'holdingreg': 'h',
    'c': 'c', '1': 'c', '0x01': 'c', 'co': 'c', 'coils': 'c',
    'd': 'd', '2': 'd', '0x02': 'd', 'di': 'd', 'discreteinput': 'd',
}

# Can this register be read or written?
mode_types = ('r', 'w', 'rw')


def check_used(used) -> bool:
    if used is None:
        # column is empty which will be interpreted as True since the column is optional
        return True

    if isinstance(used, bool):
        return used

    if isinstance(used, int):
        return bool(int)

    if isinstance(used, str):
        used = used.lower().strip()
        if len(used) == 0:
            return True  # empty string which will be interpreted as True since the column is optional

        valid = {'true': True, 't': True, '1': True, 'false': False, 'f': False, '0': False}

        try:
            return valid[used]
        except KeyError:
            raise ValueError(f'Cannot interpret string {used} as True or False value')

    raise ValueError(f'Cannot handle parameter {used} with type {type(used)}')


def check_register_type(register_type: str) -> str:
    """
    check for valid register type names by looking up in a dict of aliases (c.f. dict register_type_lookup)
    '_' and case will be ignored
    :param register_type:
    :return:
    """

    try:
        return register_type_lookup[register_type.replace('_', '').lower()]
    except KeyError:
        raise ValueError(f'Invalid register type: {register_type}')


def check_data_type(data_type: str) -> str:
    """
    check for valid data type names by looking up in a dict of aliases (c.f. dict data_type_lookup)
    '_' and case will be ignored
    :param data_type:
    :return:
    """

    normalized = data_type.replace('_', '').lower().strip()

    # Check if it matches the pattern for a string type (e.g. "string12")
    match = re.fullmatch(r'string(\d+)', normalized)
    if match:
        length = int(match.group(1))
        if length < 1:
            raise ValueError(f"Invalid register type: {data_type}")
        return f"string{length}"  # Return in the form "string<number>"

    try:
        return data_type_lookup[normalized]
    except KeyError:
        raise ValueError(f'Invalid register type: {data_type}')


def check_optional_string(value: Optional[str]) -> str:
    """
    a None will result in an empty string, otherwise the input is stripped and passed
    :param value:
    :return:
    """
    if value is None:
        value = ''
    return value.strip()


def check_scaling(scaling: Optional[str]) -> float | None:
    """
    None or empty string will result in 1.0, all other values will be parsed to float
    :param scaling:
    :return:
    """
    if scaling is None or scaling == '':
        return None
    try:
        return float(scaling.strip())
    except ValueError:
        return 1.0


def check_mode(mode: Optional[str]) -> str:
    """
    None or empty string will result in 'r', all other values will be stripped
    :param mode: Input mode
    :return: Corrected mode
    """
    if mode is None or mode == '':
        return 'r'
    if mode.strip().lower() in mode_types:
        return mode
    else:
        raise ValueError(f'Invalid mode: {mode}')
