import sys

print(
    f"""Instead of running this zipapp directly, use it in the PYTHONPATH:
PYTHONPATH="{sys.argv[0]}" python3 -m _autograder
"""
)
