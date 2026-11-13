import pytest

from modbus_crawler.input_data_validation import check_data_type, data_type_lookup

@pytest.mark.parametrize(
    ("raw_data_type", "expected"),
    [
        ("S16", "int16"),
        ("s_16", "int16"),
        ("U16", "uint16"),
        ("u_16", "uint16"),
        ("S32", "int32"),
        ("s_32", "int32"),
        ("U32", "uint32"),
        ("u_32", "uint32"),
        ("S64", "int64"),
        ("s_64", "int64"),
        ("U64", "uint64"),
        ("u_64", "uint64"),
    ],
)
def test_check_data_type_normalizes_short_integer_acronyms(raw_data_type, expected):
    assert check_data_type(raw_data_type) == expected
