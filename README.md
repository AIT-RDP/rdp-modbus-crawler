# Modbus Crawler

Generic Modbus crawler that reads and writes registers according to device and register spec.

_Author: Christian Seitl, christian.seitl@ait.ac.at_

Registers are specified either in a pandas data frame or a csv-file. The columns are:

* `Register_start`: start address of modbus read register command.
* ~~`Register_end`: end address of modbus read register command~~ Not necessary anymore. Will be calculated
  automatically from data_type size.
* `Register_type`: either `i` for input register, `h` for holding register, `c` for coil and `d` for discrete input.
* `Data_type`: Data type of variable. Depending on type the variable is kept in 1, 2 or 4 16-bit registers.
    - currently supported: BOOL, INT16, UINT16, INT32, UINT32, INT64, UINT64, SINGLE (float), DOUBLE (float), HALF (
      precision float).
    - Note: Word and byte order can be set in the constructor.
    - Note: BOOL is required for coil and discrete input registers.
    - Note: Only works on block level, i.e. all registers in a block must have the same data type. First register
      defines the block data type.
* `Name` of variable.
* `Unit` of variable _(optional, not used in the code)_.
* `Scaling` of variable _(optional column, default None)_: Often fixed point values are stored in a scaled INT register,
  which is an easy way to store comma values in one single register
    - e.g. `U_L1 = 23174` and `Scaling = 0.01` which lead to `U_L1 = 231.74` .
    - When using 'scaling = 1' on an int register, the value will be returned as a float.
    - If float uses 'scaling = 1' the value will not be changed to avoid floating point errors.
    - Any other scaling values will return a float.
* `Used` _(optional column, default True)_: If `False`, the block will be ignored.
    - Note: Only works on block level, i.e. all registers in a block must have the same value. First register defines
      the block value.
* `Unit_ID` _(optional column, default 1)_: Unit ID (Slave ID) when sending the read register command.
    - Note: Only works on block level, i.e. all registers in a block must have the same Unit_ID. First register defines
      the block Unit_ID.
* `description` _(optional column, not used int the code)_: Description of the variable.
* `mode` _(optional column, default 'r')_: If the variable should be read ('r') or written ('w') or both ('rw').
    - Note: Only works on block level, i.e. all registers in a block must have the same mode. First register defines the
      block mode.

Example:

| Register_start | Register_end | Register_type | Data_type | Name | Unit | Scaling |
|----------------|--------------|---------------|-----------|------|------|---------|
| 100            | 100          | i             | INT16     | I_L1 | A    | 0.01    |
| 110            | 111          | i             | SINGLE    | f    | Hz   | 1       |
| 200            | 205          | i             | SINGLE    | U_L1 | V    | 1       |
| x              | x            | i             | SINGLE    | U_L2 | V    | 1       |
| x              | x            | i             | SINGLE    | U_L3 | V    | 1       |

* Registers are read in blocks. A block is defined from `Register_start` until the line above the next number in the
  column `Register_start`.
* First line will read one register (100), decode the bytes as `INT16` multiple with 0.01
* Second line will read two registers (110 to 11), decode as single float
* Third line will read six registers (200 to 205), decode the first two as single, store into `U_L1`, the next two into
  `U_L2` and so on
* This is done to reduce number of read commands which saves time and traffic (reading 50 registers at once vs. 50 times
  one register)
* Some Modbus devices force you to read a list of single floats pairwise (e.g. some SMA inverters). Then the entries
  would be 200-201, 202-203, 204-205
    * Note: due to Modbus protocol definition, only 123 registers can read at once
* Header row is not case-sensitive and can also be in snake-case, e.g.:
    * `datatype` -> `datatype`
    * `DataType` -> `datatype`
    * `DATATYPE` -> `datatype`
    * `data_type` -> `datatype`
* Entries in columns `Register_type` and `Data_type` are case-insensitive too, but don't use snake case
* Strings are supported to read and write with the `data_type`: `stringX` where `X` is the number of registers the
  string uses which is always half the size of the string bytes because one register has 2 bytes. When writing the
  string will be padded with spaces to the right to fill the registers. Up to 128 registers can be read at once (256
  bytes).
    * e.g. `string10` reads 10 characters from the registers striping white spaces at the start or end
* [input_data_validation.py](modbus_crawler/input_data_validation.py) defines some aliases for register and data types,
  e.g. (subset)
    * `int`: `int16`, `short`
    * `uint`: `uint16`, `ushort`
    * `dint`: `int32`, `long`
    * `float`: `float32`, `single`, `real`
      and
    * `i`: `4`, `0x04`, `ir`, `inputregister`, `inputreg`
    * `h`: `3`, `0x03`, `hr`, `holdingregister`, `holdingreg`
* Registers can be written to individually addressable by id or name.

## API

```python
register_spec_df = pd.read_csv("register_spec.csv")

modbus_device = ModbusTcpDevice("localhost", 502, byteorder=Endian.BIG, wordorder=Endian.BIG, auto_connect=True,
                                registers_spec_df=register_spec_df, register_specs_file_name=None)

modbus_device.connect()
registers = modbus_device.read_registers_as_dict()
modbus_device.disconnect()
```

Functions in `ModbusTcpDevice`:

```python
def connect(self):
    """Connects to the Modbus device."""


def disconnect(self):
    """Disconnects from the Modbus device."""


@property
def connected(self) -> bool:
    """Returns True if connected to the Modbus device."""


def read_registers_as_dict(self) -> dict[str, float]:
    """Reads all registers and returns them as dictionary."""


def read_registers(self) -> list[ModbusRegister]:
    """Reads all registers with mode `r` or `rw` and returns them as list of ModbusRegister objects."""


def read_register(self, register: str | int) -> ModbusRegister:
    """Reads a single register with mode `r` or `rw` and returns it as ModbusRegister object."""


def write_register(self, register: str | int, value):
    """Writes a single register."""
```