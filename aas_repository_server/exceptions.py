class OPAException(Exception):
    """Base exception all other `opa` exceptions are derived from."""
class InvalidPolicy(OPAException):
    """The policy provided was not valid."""