from typing import Any, Type


def check_var_types(*type_pairs: tuple[Any, Type]):
    for var, _type in type_pairs:
        yield isinstance(var, _type)
