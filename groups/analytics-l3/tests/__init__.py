"""Test package bootstrap.

Makes the suite runnable both as ``unittest discover -s tests`` and as a
package (``python -m unittest tests.test_query``) from the group root,
with or without ``PYTHONPATH=src`` already set (UNION-SPEC contract:
runnable and testable with PYTHONPATH=src).
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for _path in (_HERE, os.path.join(os.path.dirname(_HERE), "src")):
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)
