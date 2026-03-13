import pytest
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadBuilder

from modbus_crawler.modbus_device import ModbusDevice
from modbus_crawler.modbus_device_async import AsyncModbusDevice
from modbus_crawler.register_block import ModbusRegister, RegisterBlock


class _Response:
    def __init__(self, registers):
        self.registers = registers

    def isError(self):
        return False


def _build_registers():
    block = RegisterBlock(start_register=100, register_type='h', slave_id=3)
    first = ModbusRegister(name='first', data_type='uint16', register=100, block=block)
    second = ModbusRegister(name='second', data_type='uint32', register=101, block=block)
    block.add_register_to_list(first)
    block.add_register_to_list(second)
    return block, first, second


def _build_response_registers():
    builder = BinaryPayloadBuilder(byteorder=Endian.BIG, wordorder=Endian.BIG)
    builder.add_32bit_uint(0x10203040)
    return builder.to_registers()


def test_read_register_decodes_only_requested_register():
    block, _, second = _build_registers()
    device = ModbusDevice(register_block_list=[block])

    def read_function(address, count, slave):
        assert (address, count, slave) == (101, 2, 3)
        return _Response(_build_response_registers())

    block._read_function = read_function

    register = device.read_register('second')

    assert register.name == 'second'
    assert register.value == 0x10203040


@pytest.mark.asyncio
async def test_read_register_async_decodes_only_requested_register():
    block, _, second = _build_registers()
    device = AsyncModbusDevice(register_block_list=[block])

    async def read_function(address, count, slave):
        assert (address, count, slave) == (101, 2, 3)
        return _Response(_build_response_registers())

    block._read_function = read_function

    register = await device.read_register(second.register)

    assert register.name == 'second'
    assert register.value == 0x10203040
