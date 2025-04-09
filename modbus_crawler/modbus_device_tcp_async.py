from pymodbus.client import AsyncModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ModbusException

from modbus_crawler.modbus_device_async import AsyncModbusDevice


class AsyncModbusTcpDevice(AsyncModbusDevice):
    def __init__(self, ip_address, modbus_port, byteorder=Endian.BIG, wordorder=Endian.BIG,
                 registers_spec_df=None, register_specs_file_name=None):
        super().__init__(byteorder=byteorder, wordorder=wordorder,
                         register_specs_file_name=register_specs_file_name,
                         registers_spec_df=registers_spec_df)

        self.ip_address = ip_address
        self.modbus_port = modbus_port

    async def connect(self):
        if self._client is None:
            self._client: AsyncModbusTcpClient = AsyncModbusTcpClient(host=self.ip_address, port=self.modbus_port)

            if self.register_block_list is not None:
                # the idea is to set the client and especially the read function once at startup (or whenever connection
                # is reset), which takes some time but then have a fast function handle for every of the hundreds/...
                # reads that will follow
                self._set_modbus_client_in_block_list()

        if not await self._client.connect():
            raise ModbusException(
                f'Could not connect to Modbus device at IP address: {self.ip_address} and port: {self.modbus_port}')

    def disconnect(self):
        self._client.close()

    @property
    def client(self) -> AsyncModbusTcpClient:
        return self._client

    @property
    def connected(self) -> bool:
        if self._client is None:
            return False

        return self._client.connected
