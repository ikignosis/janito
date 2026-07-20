from dataclasses import dataclass


@dataclass
class Privileges:
    READ: bool = False
    WRITE: bool = False
    EXEC: bool = False


running_privileges = None
