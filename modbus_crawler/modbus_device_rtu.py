from typing import Literal

from pymodbus import ModbusException
from pymodbus.client import ModbusSerialClient
from pymodbus.constants import Endian

from modbus_crawler.modbus_device import ModbusDevice


class ModbusRtuDevice(ModbusDevice):
    def __init__(self,
                 com_port: str,
                 baudrate: int = 9600,
                 parity: Literal['E', 'O', 'N'] = 'N',
                 stopbits: int = 1,
                 bytesize: int = 8,
                 timeout: int = 3,
                 byteorder: Endian = Endian.BIG,
                 wordorder: Endian = Endian.BIG,
                 registers_spec_df=None,
                 register_specs_file_name=None):
        super().__init__(byteorder=byteorder, wordorder=wordorder,
                         register_specs_file_name=register_specs_file_name,
                         registers_spec_df=registers_spec_df)

        self.com_port = com_port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.timeout = timeout

    def connect(self):
        if self._client is None:
            self._client: ModbusSerialClient = ModbusSerialClient(port=self.com_port, baudrate=self.baudrate,
                                                                  parity=self.parity, stopbits=self.stopbits,
                                                                  bytesize=self.bytesize,
                                                                  timeout=self.timeout)

            if self.register_block_list is not None:
                # the idea is to set the client and especially the read function once at startup (or whenever connection
                # is reset), which takes some time but then have a fast function handle for every of the hundreds/...
                # reads that will follow
                self._set_modbus_client_in_block_list()

        if not self._client.connect():
            raise ModbusException(
                f'Could not connect to Modbus RTU device on com port {self.com_port}')

    def disconnect(self):
        self._client.close()

    @property
    def client(self) -> ModbusSerialClient:
        return self._client

    @property
    def connected(self) -> bool:
        if self._client is None:
            return False

        return self._client.connected
