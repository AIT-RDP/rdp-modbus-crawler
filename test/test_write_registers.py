from unittest.mock import MagicMock

import pytest
from pymodbus.constants import Endian

from modbus_crawler.modbus_device_tcp import ModbusTcpDevice
from modbus_crawler.modbus_device_tcp_async import AsyncModbusTcpDevice
from test_write_read import run_modbus_server

# A command block of 8 registers, as a device expects it in one request: two 16-bit, two 32-bit and two 16-bit values
COMMAND = {'mode': 1, 'exec_mode': 1, 'ac_power': -1000, 'ac_reactive_power': 0, 'duration': 90, 'timeout': 30}


def spy(device, method_name):
    """Count the calls of a client method while still sending them (pymodbus returns an awaitable, not a coroutine
    function, so a MagicMock passes it through for the async client too)."""
    original = getattr(device.client, method_name)
    mock = MagicMock(side_effect=original)
    setattr(device.client, method_name, mock)
    return mock


@pytest.mark.asyncio
async def test_write_registers_async_sends_one_request():
    run_modbus_server(0, 100, 5050)
    mbc = AsyncModbusTcpDevice(ip_address="localhost", modbus_port=5050, wordorder=Endian.LITTLE,
                               register_specs_file_name="registers_test_write_multiple.csv")
    await mbc.connect()
    write_registers = spy(mbc, 'write_registers')
    write_register = spy(mbc, 'write_register')

    # Given out of order, sent from the lowest register on
    await mbc.write_registers(dict(reversed(COMMAND.items())))

    write_registers.assert_called_once()
    assert write_registers.call_args.args[0] == 10
    assert write_registers.call_args.args[1] == [1, 1, 0xFC18, 0xFFFF, 0, 0, 90, 30]
    write_register.assert_not_called()
    data = await mbc.read_registers_as_dict()
    assert {name: data[name] for name in COMMAND} == COMMAND

    # One 16-bit register goes out as "write multiple registers" as well
    await mbc.write_registers({'mode': 0})
    assert write_registers.call_count == 2 and write_registers.call_args.args[1] == [0]
    write_register.assert_not_called()
    assert (await mbc.read_registers_as_dict())['mode'] == 0

    mbc.disconnect()


def test_write_registers_sync():
    run_modbus_server(0, 100, 5051)
    mbc = ModbusTcpDevice(ip_address="localhost", modbus_port=5051,
                          register_specs_file_name="registers_test_write_multiple.csv")
    mbc.connect()
    write_registers = spy(mbc, 'write_registers')

    mbc.write_registers(COMMAND)

    write_registers.assert_called_once()
    data = mbc.read_registers_as_dict()
    assert {name: data[name] for name in COMMAND} == COMMAND
    mbc.disconnect()


def test_write_registers_refuses_gaps_and_empty():
    mbc = ModbusTcpDevice(ip_address="localhost", modbus_port=5052, auto_connect=False,
                          register_specs_file_name="registers_test_write_multiple.csv")
    mbc._client = MagicMock()

    with pytest.raises(ValueError, match='gap'):
        mbc.write_registers({'mode': 1, 'ac_power': 5})  # exec_mode is missing in between
    with pytest.raises(ValueError, match='gap'):
        mbc.write_registers({'timeout': 1, 'other': 2})  # other is in another block further on
    with pytest.raises(ValueError):
        mbc.write_registers({})
    mbc.client.write_registers.assert_not_called()
