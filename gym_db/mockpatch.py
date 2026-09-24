"""Offline-testing shim: teaches mongomock the $round operator (native in MongoDB 4.2+).
Only loaded when running with --mock; it has no effect on a real MongoDB server."""
from mongomock import aggregate as _agg

_agg.binary_arithmetic_operators.add("$round")
_agg.arithmetic_operators.add("$round")
_orig = _agg._Parser._handle_arithmetic_operator


def _patched(self, operator, values):
    if operator == "$round":
        num, places = self.parse_many(values)
        return None if num is None else round(num, int(places))
    return _orig(self, operator, values)


_agg._Parser._handle_arithmetic_operator = _patched
