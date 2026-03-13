# Modbus Crawler

`modbus-crawler` reads and writes Modbus registers from a simple register specification. It supports Modbus TCP and
Modbus RTU, sync and async clients, and CSV or pandas-based register definitions.

The main idea is straightforward: define registers once, let the library group them into efficient read blocks, and
work with decoded Python values instead of raw register payloads.

## Installation

```bash
pip install .
```

Optional extras:

- `pip install ".[test]"` for tests
- `pip install pandas` if you want to pass a `DataFrame`

## What It Supports

- Modbus TCP: `ModbusTcpDevice`, `AsyncModbusTcpDevice`
- Modbus RTU: `ModbusRtuDevice`, `AsyncModbusRtuDevice`
- Register specs from CSV, pandas, or pre-built `RegisterBlock` objects
- Datatypes: `int16`, `uint16`, `int32`, `uint32`, `int64`, `uint64`, `float16`, `float32`, `float64`, `bool`, `string1` to `string128`
- Access by register name or register address

## Quick Start

```python
from pymodbus.constants import Endian

from modbus_crawler.modbus_device_tcp import ModbusTcpDevice

device = ModbusTcpDevice(
    ip_address="127.0.0.1",
    modbus_port=502,
    byteorder=Endian.BIG,
    wordorder=Endian.BIG,
    register_specs_file_name="registers.csv",
)

data = device.read_registers_as_dict()
register = device.read_register("Voltage_L1")
device.write_register("Setpoint", 42)
device.disconnect()
```

Async TCP works the same way, but with `await`:

```python
import asyncio

from modbus_crawler.modbus_device_tcp_async import AsyncModbusTcpDevice


async def main():
    device = AsyncModbusTcpDevice(
        ip_address="127.0.0.1",
        modbus_port=502,
        register_specs_file_name="registers.csv",
    )
    await device.connect()
    data = await device.read_registers_as_dict()
    await device.write_register("Setpoint", 42)
    device.disconnect()


asyncio.run(main())
```

## Register Specification

Register specs can come from:

- a CSV file
- a pandas `DataFrame`
- a list of `RegisterBlock` objects

Column names are matched case-insensitively and with underscores removed. `Data_type`, `datatype`, and `DataType`
are treated the same.

### Required columns

- `Register_start`
- `Register_type`
- `Data_type`
- `Name`

### Optional columns

- `Unit`
- `Scaling`
- `Unit_id`
- `Used`
- `Description`
- `mode`
- `Register_end`

`Register_end` is accepted for compatibility, but it is not used. Register lengths are derived from `Data_type`.

### Example

```csv
Register_start,Register_type,Data_type,Name,Unit,Scaling,Unit_id,Used,mode,Description
100,i,float,Grid_Frequency,Hz,1,1,,r,Grid frequency
-,,,float,Voltage_L1,V,1,,,Phase L1 voltage
-,,,float,Voltage_L2,V,1,,,Phase L2 voltage
-,,,float,Voltage_L3,V,1,,,Phase L3 voltage
200,h,int,Power_Limit,%,1,1,,rw,Writable power limit
202,h,string10,Serial_Number,,,,,Device serial number
300,c,bool,Enable_Output,,,1,,rw,Output enable coil
```

## How Blocks Work

A new block starts whenever `Register_start` contains a number. Rows below it belong to that block until the next
explicit start address.

These values mean "continue the current block":

- empty
- `x`
- `-`
- `_`
- `none`

Block-level settings come from the first row in the block:

- `Register_start`
- `Register_type`
- `Unit_id`
- `Used`
- `mode`

If you mix those values inside one block, the first row wins.

## Register Types

Canonical values:

- `i` for input registers
- `h` for holding registers
- `c` for coils
- `d` for discrete inputs

Accepted aliases:

| Canonical | Aliases |
|-----------|---------|
| `i` | `4`, `0x04`, `ir`, `inputregister`, `inputreg` |
| `h` | `3`, `0x03`, `hr`, `holdingregister`, `holdingreg` |
| `c` | `1`, `0x01`, `co`, `coils` |
| `d` | `2`, `0x02`, `di`, `discreteinput` |

## Data Types

Accepted datatype aliases:

| Canonical | Aliases |
|-----------|---------|
| `int16` | `int`, `short`, `int16`, `s16` |
| `uint16` | `uint`, `ushort`, `uint16`, `u16` |
| `int32` | `dint`, `long`, `int32`, `s32` |
| `uint32` | `ulong`, `uint32`, `u32` |
| `int64` | `int64`, `s64` |
| `uint64` | `uint64`, `u64` |
| `float16` | `half`, `float16` |
| `float32` | `float`, `single`, `real`, `float32` |
| `float64` | `double`, `float64` |
| `bool` | `bool`, `bit`, `boolean`, `coil` |
| `stringN` | `string1` to `string128` |

Register width:

| Data type | Registers |
|-----------|-----------|
| `bool`, `int16`, `uint16`, `float16` | 1 |
| `int32`, `uint32`, `float32` | 2 |
| `int64`, `uint64`, `float64` | 4 |
| `stringN` | `N` |

Notes:

- `string10` means 10 Modbus registers, not 10 characters
- `string0` is invalid
- short forms like `s16`, `u16`, `s32`, `u32`, `s64`, `u64` are supported

## Validation Rules

- `Register_start` must be an integer from `0` to `65535`
- coils and discrete inputs must use datatype `bool`
- coils and discrete inputs cannot use scaling
- `bool` should not use scaling
- strings should be left unscaled as well
- `Used` defaults to `True`
- `Unit_id` defaults to `1`
- `mode` defaults to `r`

Valid `mode` values:

- `r`
- `w`
- `rw`

Valid `Used` inputs:

- true: `true`, `t`, `1`, empty
- false: `false`, `f`, `0`

## Reading and Writing

`read_registers()` reads all blocks whose mode includes `r` and returns a list of `ModbusRegister` objects.

`read_registers_as_dict()` does the same but returns a dictionary keyed by register name.

`read_register(register)` reads a single register by name or address. This also works for registers in `w` blocks.

`write_register(register, value)` writes a single register by name or address. Values are cast to the configured type
before encoding. Scaled values are converted back to raw register values before writing.

One important detail: the library does not enforce `mode` on writes. A register marked as `r` can still be written if
you call `write_register(...)`.

## Endianness

Byte order and word order are configurable on all device classes through `byteorder` and `wordorder`.

```python
from pymodbus.constants import Endian

device = ModbusTcpDevice(
    ip_address="127.0.0.1",
    modbus_port=502,
    byteorder=Endian.LITTLE,
    wordorder=Endian.BIG,
    register_specs_file_name="registers.csv",
)
```

## pandas Input

```python
import pandas as pd

from modbus_crawler.modbus_device_tcp import ModbusTcpDevice

df = pd.read_csv("registers.csv")

device = ModbusTcpDevice(
    ip_address="127.0.0.1",
    modbus_port=502,
    registers_spec_df=df,
)
```

## Programmatic Specs

If you already build register definitions in code, you can pass `RegisterBlock` objects directly:

```python
from modbus_crawler.modbus_device_tcp import ModbusTcpDevice
from modbus_crawler.register_block import ModbusRegister, RegisterBlock

block = RegisterBlock(start_register=100, register_type="h", slave_id=1, mode="rw")
register = ModbusRegister(name="Setpoint", data_type="int16", register=100, block=block)
block.add_register_to_list(register)

device = ModbusTcpDevice(ip_address="127.0.0.1", modbus_port=502, auto_connect=False)
device.set_registers_spec(register_block_list=[block])
device.connect()
```

## Scheduling

Synchronous devices support periodic reads through the `schedule` package:

```python
import schedule

from modbus_crawler.modbus_device_tcp import ModbusTcpDevice


def handle_data(registers):
    print(registers)


device = ModbusTcpDevice(
    ip_address="127.0.0.1",
    modbus_port=502,
    register_specs_file_name="registers.csv",
)

device.schedule(schedule.every(5).seconds, handle_data)
device.run()
```

The callback receives the result of `read_registers()`.

## Limitations

- async devices do not implement scheduling helpers
- `run(blocking=False)` is not implemented
- there is no CLI
- `Register_end` is ignored

## Development

```bash
$env:PYTHONPATH='.'
pytest
```
