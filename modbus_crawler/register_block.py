from dataclasses import dataclass

from pymodbus.client import ModbusBaseClient
from pymodbus.exceptions import ModbusException

from modbus_crawler.input_data_validation import data_types, register_types

# Number of registers necessary to represent a given data type. Names must match an entry in 'data_type_lookup' in '
# 'input_data_validation.py'
register_span = {'uint16': 1, 'int16': 1, 'uint32': 2, 'int32': 2,
                 'uint64': 4, 'int64': 4,
                 'float16': 1, 'float32': 2, 'float64': 4, 'bool': 1, **{f'string{i}': i for i in range(129)}
                 }

@dataclass(repr=True)
class ModbusRegister:
    name: str
    data_type: str
    register: int
    value: float | int | str = 0
    unit: str = None  # SI unit, not modbus unit=slave
    description: str = None
    block: 'RegisterBlock' = None
    mode: str = 'r'  # read or write or readwrite
    scaling: float | None = None  # raw register values will be multiplied by this before setting value attribute

    # Often fixed point values are stored in a scaled int register, which is an easy way to store comma values in one single register
    # Or the register gives Ws, but we want kWh

    def __post_init__(self):
        if self.data_type not in data_types:
            raise ValueError(f'data type must be one of {data_types}, but is {self.data_type}')

    @property
    def length(self) -> int:
        return register_span[self.data_type]

    def asdict(self) -> dict[str, str | float]:
        return {'name': self.name,
                'value': self.value,
                'unit': self.unit,
                'description': self.description}


class RegisterBlock:
    def __init__(self, start_register: int, slave_id: int = 1, register_type: str = 'i', mode: str = 'r'):
        """

        :param start_register:
        :param slave_id: optional, default=1
        :param register_type: type of registers, e.g. input register or holding register (for the whole block since a block is read with single read command
        """
        self.start_register = start_register
        self.slave_id = slave_id

        if register_type not in register_types:
            raise ValueError(f'register type must be one of {register_types}, but is {register_type}')
        self.register_type = register_type
        self.mode = mode

        self._block_length = 0
        self._register_list = list[ModbusRegister]()

        self._read_function = None

    def add_register_to_list(self, modbus_register: ModbusRegister):
        self._register_list.append(modbus_register)
        self._block_length += modbus_register.length

    @property
    def register_list(self) -> list[ModbusRegister]:
        return self._register_list

    def set_modbus_device(self, modbus_client: ModbusBaseClient):
        if self.register_type == 'i':
            self._read_function = modbus_client.read_input_registers
        elif self.register_type == 'h':
            self._read_function = modbus_client.read_holding_registers
        elif self.register_type == 'c':
            self._read_function = modbus_client.read_coils
        else:
            self._read_function = modbus_client.read_discrete_inputs

    def read_registers(self):
        if self._read_function is None:
            raise RuntimeError('you have to call set_modbus_device() first')

        resp = self._read_function(address=self.start_register,
                                   count=self._block_length,
                                   slave=self.slave_id)
        if resp.isError():
            raise ModbusException(
                f'Could not read {self._block_length} registers, starting from {self.start_register} with slave id {self.slave_id}: {resp}')
        return resp

    async def read_registers_async(self):
        if self._read_function is None:
            raise RuntimeError('you have to call set_modbus_device() first')

        resp = await self._read_function(address=self.start_register,
                                         count=self._block_length,
                                         slave=self.slave_id)
        if resp.isError():
            raise ModbusException(
                f'Could not read {self._block_length} registers, starting from {self.start_register} with slave id {self.slave_id}')

        return resp

    @property
    def block_length(self):
        return self._block_length
