from abc import ABC, abstractmethod

from modbus_crawler.register_block import RegisterBlock


class ModbusRegisterListParserInterface(ABC):
    @staticmethod
    @abstractmethod
    def get_register_list(*args, **kwargs) -> list[RegisterBlock]:
        pass
