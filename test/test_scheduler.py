"""
    To test the crawler...

    ... we start a simple modbus server that sets random register values every n-seconds
        (Basically a copy from pymodbus server example with some small changes)

    ... read the registers every 5 seconds

    Author: Christian Seitl, christian.seitl@ait.ac.at
    Date: June 2020
"""
import multiprocessing
import threading

import pytest
from pymodbus.server import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext

from modbus_crawler.modbus_device_tcp import ModbusTcpDevice
from schedule import Job


def run_modbus_server(start_input_registers, number_of_input_registers,
                      port=502):
    def run_updating_server():
        store = ModbusSlaveContext(
            ir=ModbusSequentialDataBlock(start_input_registers + 1, [151] * number_of_input_registers),
        )

        context = ModbusServerContext(slaves=store, single=True)

        t = threading.Thread(target=StartTcpServer,
                             daemon=True,
                             kwargs={'context': context, 'identity': ModbusDeviceIdentification(),
                                     'address': ("0.0.0.0", port)})

        t.start()

    run_updating_server()


def start_crawling():
    def callback(data):
        assert len(data) == 45, f"Expected 45 registers, got {len(data)}"

    mbc = ModbusTcpDevice(ip_address="localhost",
                          modbus_port=5171,
                          register_specs_file_name="registers_test_read.csv")

    mbc.schedule(Job(1).seconds, callback)

    mbc.run(blocking=True)

def test_scheduler():
    run_modbus_server(start_input_registers=0, number_of_input_registers=19120,
                      port=5171)

    process = multiprocessing.Process(target=start_crawling)
    process.start()
    process.join(5)  # Wait for the process with a timeout

    # Check if process crashed
    if process.exitcode is not None:
        pytest.fail(process.exitcode)

    if process.is_alive():
        process.terminate()  # Kill the process
