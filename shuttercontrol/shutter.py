from __future__ import annotations

from enum import Enum

from shuttercontrol.gpio import GPIOBoard
from shuttercontrol.shutterstate import ShutterState


class ShutterState(Enum):
    CLOSED: int = 0
    OPEN: int = 1


class Shutter:

    def __init__(self, board: GPIOBoard) -> None:
        self.__board = board
        self.__state = None

    def open(self) -> None:
        if self.__state is ShutterState.OPEN:
            # Shutter is already open
            return None

        self.__board.trigger_open()
        self.__state = ShutterState.OPEN

    def close(self) -> None:
        if self.__state is ShutterState.CLOSED:
            # Shutter is already closed
            return None
        
        self.__board.trigger_close()
        self.__state = ShutterState.CLOSED
