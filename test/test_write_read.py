import threading
from math import isclose

import pytest
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.server import StartTcpServer

from modbus_crawler.modbus_device_tcp import ModbusTcpDevice
from modbus_crawler.modbus_device_tcp_async import AsyncModbusTcpDevice


def run_modbus_server(start_input_registers, number_of_input_registers, port):
    store = ModbusSlaveContext(
        ir=ModbusSequentialDataBlock(start_input_registers + 1, [0] * number_of_input_registers),
        hr=ModbusSequentialDataBlock(start_input_registers + 1, [0] * number_of_input_registers),
        co=ModbusSequentialDataBlock(start_input_registers + 1, [0] * number_of_input_registers),
        di=ModbusSequentialDataBlock(start_input_registers + 1, [0] * number_of_input_registers),
    )

    context = ModbusServerContext(slaves=store, single=True)

    def run_updating_server():
        t = threading.Thread(target=StartTcpServer, daemon=True,
                             kwargs={'context': context, 'identity': ModbusDeviceIdentification(),
                                     'address': ("0.0.0.0", port)})
        t.start()

    run_updating_server()


# Values with max values of each type
write_test_values = [
    3.4028234663852886e+38,  # float
    3.4028234663852886e+38,  # float
    32767,  # int
    65535,  # uint
    2147483647,  # dint
    4294967295,  # ulong
    9223372036854775807,  # int64
    18446744073709551614,  # uint64
    65504,  # float16
    3.4028234663852886e+38,  # float
    1.7976931348623157e+308,  # double
    123, # int scaled to 0.1
    5234, # int scaled to 2
    234, # int scaled to 1 and converted to float
    "Hello World",  # string
    "This is me",  # string
    123.5678,  # Scaled float
    423.2342,  # Scaled float
    True,  # Bool with input register
    False,  # Bool with input register
    True, # Bool with coil
    False,  # Bool with coil
]

check_types = [
    float,
    float,
    int,
    int,
    int,
    int,
    int,
    int,
    float,
    float,
    float,
    float,
    float,
    float,
    str,
    str,
    float,
    float,
    bool,
    bool,
    bool,
    bool
]

def compare_special_values(data):
    assert data["String_1"] == write_test_values[14], f"Register String_1 has value {data["String_1"]} and should be {write_test_values[14]}"
    assert data["String_2"] == write_test_values[15], f"Register String_2 has value {data["String_2"]} and should be {write_test_values[15]}"

    assert isclose(data["Scaled_Zahl_1"], write_test_values[16], abs_tol=1e-4), f"Register Scaled_Zahl_1 has value {data["Scaled_Zahl_1"]} and should be {write_test_values[16]}"
    assert isclose(data["Scaled_Zahl_2"], write_test_values[17], abs_tol=1e-4), f"Register Scaled_Zahl_2 has value {data["Scaled_Zahl_2"]} and should be {write_test_values[17]}"

    assert data["Bool_1"] is write_test_values[18], f"Register Bool_1 has value {data["Bool_1"]} and should be {write_test_values[18]}"
    assert data["Bool_2"] is write_test_values[19], f"Register Bool_2 has value {data["Bool_2"]} and should be {write_test_values[19]}"
    assert data["Bool_3"] is write_test_values[20], f"Register Bool_3 has value {data["Bool_3"]} and should be {write_test_values[20]}"
    assert data["Bool_4"] is write_test_values[21], f"Register Bool_4 has value {data["Bool_4"]} and should be {write_test_values[21]}"

@pytest.mark.asyncio
async def test_write_async():
    run_modbus_server(0, 200, 5041)

    mbc = AsyncModbusTcpDevice(ip_address="localhost",
                               modbus_port=5041,
                               register_specs_file_name="registers_test_write.csv")

    await mbc.connect()

    # Write all values
    for i, register in enumerate(await mbc.read_registers()):
        print(f"Writing {write_test_values[i]} to register {register.name} ({register.register})")
        await mbc.write_register(register.register, write_test_values[i])

    # Read all values and compare
    registers = await mbc.read_registers()
    for i, register in enumerate(registers[:14]):
        assert register.value == write_test_values[i], f"Register {register.name} has value {register.value} and should be {write_test_values[i]}"

    for i, register in enumerate(registers):
        assert isinstance(register.value, check_types[i]), f"Register {register.name} has type {type(register.value)} and should be {check_types[i]}"

    data = await mbc.read_registers_as_dict()

    compare_special_values(data)

    mbc.disconnect()


def test_write():
    run_modbus_server(0, 200, 5030)

    mbc = ModbusTcpDevice(ip_address="localhost",
                          modbus_port=5030,
                          register_specs_file_name="registers_test_write.csv")

    mbc.connect()

    # Write all values
    for i, register in enumerate(mbc.read_registers()):
        print(f"Writing {write_test_values[i]} to register {register.name} ({register.register})")
        mbc.write_register(register.register, write_test_values[i])

    # Read all values and compare
    registers = mbc.read_registers()
    for i, register in enumerate(registers[:14]):
        assert register.value == write_test_values[i], f"Register {register.name} has value {register.value} and should be {write_test_values[i]}"

    for i, register in enumerate(registers):
        assert isinstance(register.value, check_types[i]), f"Register {register.name} has type {type(register.value)} and should be {check_types[i]}"

    data = mbc.read_registers_as_dict()

    compare_special_values(data)

    mbc.disconnect()

def test_read():
    run_modbus_server(start_input_registers=0, number_of_input_registers=19120, port=5020)

    mbc = ModbusTcpDevice(ip_address="localhost",
                          modbus_port=5020,
                          register_specs_file_name="registers_test_read.csv")

    data = mbc.read_registers_as_dict()
    data_expected = [
        'f', 'U_zero', 'U_neg', 'U_pos', 'U_L1N', 'U_L2N', 'U_L3N', 'U_L12', 'U_L23', 'U_L31', 'I_L1', 'I_L2', 'I_L3',
        'I_tot', 'P_L1', 'P_L2', 'P_L3', 'P_tot', 'Q_L1', 'Q_L2', 'Q_L3', 'Q_tot', 'S_L1', 'S_L2', 'S_L3', 'S_tot',
        'P0_L1', 'P0_L2', 'P0_L3', 'P0_tot', 'D_L1', 'D_L2', 'D_L3', 'D_tot', 'THD_I_L1', 'THD_I_L2', 'THD_I_L3',
        'THD_I_tot', 'TDD_I_L1', 'TDD_I_L2', 'TDD_I_L3', 'TDD_I_tot', 'I_zero', 'I_pos', 'I_neg'
    ]

    assert list(data.keys()) == data_expected

if __name__ == "__main__":
    test_write()