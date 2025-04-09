from modbus_crawler.modbus_register_list_parser import ModbusRegisterListParserInterface
from modbus_crawler.modbus_register_list_parser_csv import CsvStringParser
from modbus_crawler.register_block import RegisterBlock

class PandasDataFrameParser(ModbusRegisterListParserInterface):

    @staticmethod
    def get_register_list(df: any) -> list[RegisterBlock]:
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("Pandas is not installed. Please install pandas to use this function.")

        return CsvStringParser.get_register_list(csv_data=df.to_csv())
