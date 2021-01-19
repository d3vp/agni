""" _begin_config_
points = 1
_end_config_ """


# _begin_code_
from hello_numbers import is_even
result = is_even(10)
if not result:
    raise AssertionError(f"is_even() returned incorrect value: {result}")
print("Test passed.")
# _end_code_
