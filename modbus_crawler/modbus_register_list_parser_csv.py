import csv
from typing import Union, Iterable, Optional

from modbus_crawler.input_data_validation import check_optional_string, check_data_type, check_register_type, \
    check_scaling, check_used, check_mode
from modbus_crawler.modbus_register_list_parser import ModbusRegisterListParserInterface
from modbus_crawler.register_block import RegisterBlock, ModbusRegister


class CsvFileParser(ModbusRegisterListParserInterface):
    @staticmethod
    def get_register_list(csv_file_name, csv_dialect='excel') -> list[RegisterBlock]:
        with open(csv_file_name, 'r') as file:
            data = file.readlines()

        return CsvStringParser.get_register_list(csv_data=data, csv_dialect=csv_dialect)


class CsvStringParser(ModbusRegisterListParserInterface):
    @staticmethod
    def get_register_list(csv_data: Union[str, Iterable[str]], csv_dialect='excel') -> list[RegisterBlock]:

        if isinstance(csv_data, str):
            csv_data = csv_data.splitlines()  # Convert the input to a list of lines, if needed

        # remove '_' and make all column names lower case to ignore case and snake case
        csv_data[0] = csv_data[0].replace('_', '').lower()

        csv_file = csv.DictReader(csv_data, dialect=csv_dialect)

        block = None
        register_block_list = list[RegisterBlock]()

        used = True  # if current register block in CSV will be use or ignored

        for row in csv_file:
            register_start = CsvStringParser._resolve_register(row['registerstart'])
            if register_start is not None:  # let's start a new block
                if block is not None:  # we already have an existing block, so add the old one to the list
                    if used:  # if the old block
                        register_block_list.append(block)

                used = check_used(row.get('used', None))  # Make the entire column optionals
                register_type = check_register_type(row['registertype'])

                unit_id_raw = row.get('unitid', None)
                unit_id = int(unit_id_raw) if (unit_id_raw != '' and unit_id_raw is not None) else 1
                mode = check_mode(row['mode']) if 'mode' in row else 'r'

                block = RegisterBlock(start_register=register_start, register_type=register_type, slave_id=unit_id,
                                      mode=mode)

            if not used:
                # if the current block is not used later on, continue iterating with next row until you find a new block
                continue

            if block is None:
                raise ValueError(f"No valid registerstart is entered at the first position: '{row['registerstart']}'")

            # obligatory columns
            name = row['name'].strip()
            data_type = check_data_type(row['datatype'])

            # optional columns
            unit = check_optional_string(row['unit']) if 'unit' in row else ''
            description = check_optional_string(row['description']) if 'description' in row else ''
            scaling = check_scaling(row['scaling']) if 'scaling' in row else None
            mode = check_mode(row['mode']) if 'mode' in row else 'r'

            # If the register_type is a coil or discrete input the data_type must be bool
            if block.register_type in {'c', 'd'} and data_type != 'bool':
                raise ValueError(
                    f"Data type must be bool for register type {block.register_type}, but is {data_type} at register {name}")

            # If the register_type is a coil or discrete input the scaling must be 1.0
            if block.register_type in {'c', 'd'} and scaling != None:
                raise ValueError(
                    f"Scaling must be None for register type {block.register_type}, but is {scaling} at register {name}")

            # Scaling must be None for bool and string data types
            if data_type in {'bool', 'string'} and scaling is not None:
                raise ValueError(f"Scaling must be None for data type {data_type}, but is {scaling} at register {name}")

            mr = ModbusRegister(name=name, data_type=data_type, register=block.start_register + block.block_length,
                                unit=unit, description=description, scaling=scaling, block=block, mode=mode)
            # print(mr)
            block.add_register_to_list(mr)

        if used:
            register_block_list.append(block)  # append last block

        return register_block_list

    @staticmethod
    def _resolve_register(reg_spec) -> Optional[int]:
        """Tries to resolve the register specification"""

        if str(reg_spec).strip().lower() in {"", "x", "-", "_", "none"}:
            return None
        try:
            # 16-bit register numbers can always be represented exactly in floats (52-bit fraction):
            ret = float(reg_spec)
        except ValueError:
            raise ValueError(f"The register specification '{reg_spec}' is not a valid number")

        if not ret.is_integer():  # Check whether the number is an integer since int(...) may nor raise reliably.
            raise ValueError(f"The register specification '{reg_spec}' is not a valid integer")
        ret = int(ret)

        if ret < 0 or ret > 0xFFFF:
            raise ValueError(f"The register specification {ret} is out of bounds (16-bit unsigned)")
        return ret
