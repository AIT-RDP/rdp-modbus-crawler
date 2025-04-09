import time
from abc import ABC
from typing import Dict

from pymodbus import ModbusException
from pymodbus.client import ModbusBaseClient
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from schedule import Scheduler, Job

from modbus_crawler.modbus_register_list_parser_csv import CsvFileParser
from modbus_crawler.modbus_register_list_parser_pandas import PandasDataFrameParser
from modbus_crawler.register_block import RegisterBlock, ModbusRegister

cast_functions = {'uint16': int, 'int16': int, 'uint32': int, 'int32': int,
                  'uint64': int, 'int64': int, 'float16': float, 'float32': float,
                  'float64': float, 'bool': bool}


class ModbusDevice(ABC):
    def __init__(self, byteorder=Endian.BIG, wordorder=Endian.BIG, register_specs_file_name: str = None,
                 registers_spec_df=None, register_block_list: list[RegisterBlock] = None):
        self._client = None
        self.wordorder = wordorder
        self.byteorder = byteorder

        self.scheduler = Scheduler()
        self._register_lookup: Dict[str | int, ModbusRegister] = {}  # Dictionary for quick lookups

        if register_specs_file_name is not None or registers_spec_df is not None or register_block_list is not None:
            self.set_registers_spec(pandas_df=registers_spec_df, csv_file_name=register_specs_file_name,
                                    register_block_list=register_block_list)
        else:
            self.register_block_list: list[RegisterBlock] | None = None

    def set_registers_spec(self, pandas_df=None, csv_file_name: str = None,
                           register_block_list: list[RegisterBlock] = None):
        if register_block_list is not None:
            self.register_block_list = register_block_list
        elif csv_file_name is not None:
            self.register_block_list: list[RegisterBlock] = CsvFileParser.get_register_list(csv_file_name)
        elif pandas_df is not None:
            self.register_block_list: list[RegisterBlock] = PandasDataFrameParser.get_register_list(pandas_df)
        else:
            raise RuntimeError('You must specify either a data frame or a csv file name')

        # Create a lookup dictionary for quick access to registers
        self._register_lookup: Dict[str | int, ModbusRegister] = {reg.name: reg for block in self.register_block_list
                                                                  for reg in block.register_list}
        self._register_lookup.update(
            {reg.register: reg for block in self.register_block_list for reg in block.register_list})

    def _set_modbus_client_in_block_list(self):
        for block in self.register_block_list:
            block.set_modbus_device(self.client)

    def read_registers_as_dict(self) -> dict[str, float]:
        return {entry.name: entry.value for entry in self.read_registers()}

    def read_registers(self) -> list[ModbusRegister]:
        """
        Read all registers marked as readable by mode specified in the register block list.
        """
        if self.register_block_list is None:
            raise RuntimeError('You must set register specification before reading registers')

        return_list = list[ModbusRegister]()
        for block in self.register_block_list:
            if 'r' in block.mode:
                resp = block.read_registers()
                return_list.extend(self._parse_response(resp, block))

        return return_list

    def read_register(self, register: str | int) -> ModbusRegister:
        """
        Read a register by name or register id. You can also read registers with mode of 'w'.

        :param register: Name or register id of the register
        :return: ModbusRegister object
        """
        modbus_register = self._register_lookup.get(register)
        if modbus_register is None:
            raise ValueError(f'Register with name or address "{register}" not found')

        resp = modbus_register.block._read_function(address=modbus_register.register,
                                                    count=modbus_register.length,
                                                    slave=modbus_register.block.slave_id)
        if resp.isError():
            raise ModbusException(
                f'Could not read {modbus_register.name} register')

        return self._parse_response(resp, modbus_register.block)[0]

    def write_register(self, register: str | int, value):
        """
        Read a register by name or register id. You can write all registers, also those with mode of 'r'.

        The value is cast and encoded to the required type before being sent.
        """

        modbus_register, prepared_value, value_type = self._prepare_write_register(register, value)

        if value_type == 'coil':
            self.client.write_coil(modbus_register.register, prepared_value, slave=modbus_register.block.slave_id)
        else:
            self.client.write_registers(modbus_register.register, prepared_value, slave=modbus_register.block.slave_id)

    def _parse_response(self, resp, block: RegisterBlock) -> list[ModbusRegister]:
        return_list = list[ModbusRegister]()

        # Special case for coils and discrete inputs
        if block.register_type == 'c' or block.register_type == 'd':
            pdc = BinaryPayloadDecoder.fromCoils(resp.bits, byteorder=self.byteorder)

            for register in block.register_list:
                decoded_value = pdc.decode_bits(register.length)
                decoded_value = any(decoded_value)
                register.value = decoded_value
                return_list.append(register)

            return block.register_list

        pdc = BinaryPayloadDecoder.fromRegisters(resp.registers, wordorder=self.wordorder,
                                                 byteorder=self.byteorder)

        decode_functions = {'uint16': pdc.decode_16bit_uint, 'int16': pdc.decode_16bit_int,
                            'uint32': pdc.decode_32bit_uint, 'int32': pdc.decode_32bit_int,
                            'uint64': pdc.decode_64bit_uint, 'int64': pdc.decode_64bit_uint,
                            'float16': pdc.decode_16bit_float, 'float32': pdc.decode_32bit_float,
                            'float64': pdc.decode_64bit_float, 'bool': pdc.decode_16bit_uint}

        for register in block.register_list:
            # Special case for strings
            # Eat up the whole string and continue with the next register
            if "string" in register.data_type:
                # Times two because the length is in register units, but the payload is in bytes
                # and one register has two bytes
                decoded_value = pdc.decode_string(register.length * 2)
                register.value = decoded_value.decode('utf-8')

                # Remove leading and trailing whitespaces
                register.value = register.value.strip()

                # Remove "\u0000" pattern which is a null byte as hex as ascii
                # Maybe this is very special to a device but it will not harm us
                register.value = register.value.replace("\u0000", '')
                register.value = register.value.replace("\x00", '')

                return_list.append(register)
                continue

            decoded_value = decode_functions[register.data_type]()

            if 'bool' in register.data_type:
                # Check if there is something in the register
                # This also cast the value to a boolean
                register.value = decoded_value > 0
            else:
                # int and float values

                # Int/uint: If scaling by 1 we scale which allows us to convert int to float
                # Float: Only multiply by scaling if scaling is not 1.0 or None to avoid floating point errors
                if register.scaling is None or (register.scaling == 1.0 and 'float' in register.data_type):
                    register.value = cast_functions[register.data_type](decoded_value)
                else:
                    # When we scale the resulting type is always a float
                    decoded_value *= register.scaling
                    register.value = decoded_value
            return_list.append(register)

        return return_list

    def _prepare_write_register(self, register: str | int, value):
        modbus_register = self._register_lookup.get(register)
        if modbus_register is None:
            raise ValueError(f'Register with name or address "{register}" not found')

        # Theoretically discrete inputs and input inputs are not writable, only coils and holding registers
        # Maybe there are devices where the value need to be written so we still support them
        if modbus_register.block.register_type == 'c' or modbus_register.block.register_type == 'd':
            if not isinstance(value, bool) and not isinstance(value, int):
                raise ValueError(f'Value for coil must be boolean or 1 or 0, but is {value}')
            return modbus_register, bool(value), 'coil'
        else:
            builder = BinaryPayloadBuilder(byteorder=self.byteorder, wordorder=self.wordorder)

            builder_add = {'uint16': builder.add_16bit_uint, 'int16': builder.add_16bit_int,
                           'uint32': builder.add_32bit_uint, 'int32': builder.add_32bit_int,
                           'uint64': builder.add_64bit_uint, 'int64': builder.add_64bit_uint,
                           'float16': builder.add_16bit_float, 'float32': builder.add_32bit_float,
                           'float64': builder.add_64bit_float, 'bool': builder.add_16bit_int}

            # Bools are sent as an integer with 0 or 1 of input registers
            # There should be coils but some devices store them as integers

            if (modbus_register.scaling is not None
                    and modbus_register.data_type != 'bool'
                    and 'string' not in modbus_register.data_type):
                value /= modbus_register.scaling

            if 'string' in modbus_register.data_type:
                # Check if string is too long
                if len(value) > modbus_register.length * 2:
                    raise ValueError(f'String is too long for register {modbus_register.name}')

                # Pad the string with spaces to the right
                # TODO: Maybe add a parameter to choose the padding left or right
                value = value.ljust(modbus_register.length * 2)

                builder.add_string(value)

                return modbus_register, builder.to_registers(), 'register'

            casted_value = cast_functions[modbus_register.data_type](value)
            builder_add[modbus_register.data_type](casted_value)

            return modbus_register, builder.to_registers(), 'register'

    def _callback_wrapper(self, callback):
        """
        Wrapper function for callbacks.

        :param callback: Callback function which has one argument. The data retrieved with "self.read_registers()"
            will be passed as argument.
        """
        data = self.read_registers()
        callback(data)

    def schedule(self, job: Job, callback):
        """
        Schedule a new job

        :param job: Job with periodicity of the timer. E.g. "schedule.Job(5).seconds"
        :param callback: Callback function which has one argument. The data retrieved with "self.read_registers()"
            will be passed as argument.
        """
        job.scheduler = self.scheduler
        job.do(self._callback_wrapper, callback=callback)

    def run(self, blocking: bool = True, t_sleep: float = .1):
        """
        Run the jobs scheduled with "self.schedule()"

        :param blocking: Should the execution be blocking
        :param t_sleep: Sleeping time between checking if jobs are pending
        """
        if blocking:
            while True:
                self.scheduler.run_pending()
                time.sleep(t_sleep)
        else:
            raise NotImplementedError

    @property
    def client(self) -> ModbusBaseClient:
        return self._client
