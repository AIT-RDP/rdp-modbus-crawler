from pymodbus import ModbusException
from schedule import Job

from modbus_crawler.modbus_device import ModbusDevice, cast_functions
from modbus_crawler.register_block import ModbusRegister


class AsyncModbusDevice(ModbusDevice):
    """
    This class overrides some methods of the ModbusDevice class to make them async.
    """

    async def read_registers_as_dict(self) -> dict[str, float]:
        return {entry.name: entry.value for entry in await self.read_registers()}

    async def read_registers(self) -> list[ModbusRegister]:
        """
        Read all registers marked as readable by mode specified in the register block list.
        """
        if self.register_block_list is None:
            raise RuntimeError('You must set register specification before reading registers')

        return_list = list[ModbusRegister]()
        for block in self.register_block_list:
            if 'r' in block.mode:
                resp = await block.read_registers_async()
                return_list.extend(self._parse_response(resp, block))

        return return_list

    async def read_register(self, register: str | int) -> ModbusRegister:
        """
        Read a register by name or register id. You can also read registers with mode of 'w'.

        :param register: Name or register id of the register
        :return: ModbusRegister object
        """
        modbus_register = self._register_lookup.get(register)
        if modbus_register is None:
            raise ValueError(f'Register with name or address "{register}" not found')

        resp = await modbus_register.block._read_function(address=modbus_register.register,
                                                    count=modbus_register.length,
                                                    slave=modbus_register.block.slave_id)
        if resp.isError():
            raise ModbusException(
                f'Could not read {modbus_register.name} register')

        return self._parse_response(resp, modbus_register.block)[0]

    async def write_register(self, register: str | int, value):
        """
        Read a register by name or register id. You can write all registers, also those with mode of 'r'.

        The value is cast and encoded to the required type before being sent.
        """

        modbus_register, prepared_value, value_type = self._prepare_write_register(register, value)

        if value_type == 'coil':
            await self.client.write_coil(modbus_register.register, prepared_value, slave=modbus_register.block.slave_id)
        else:
            await self.client.write_registers(modbus_register.register, prepared_value, slave=modbus_register.block.slave_id)


    def _callback_wrapper(self, callback):
        raise NotImplementedError

    def schedule(self, job: Job, callback):
        raise NotImplementedError

    def run(self, blocking: bool = True, t_sleep: float = .1):
        raise NotImplementedError
