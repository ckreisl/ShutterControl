import dataclasses
import shelve
import astral

from pathlib import Path
from datetime import datetime

from typing import Union


@dataclasses.dataclass
class ShutterSettings:
    close_at_dawn: bool
    open_at_time:  Union[None, datetime.time]
    depression:    Union[float, astral.Depression]
    latest:        Union[None, datetime.time]


class ShutterSettingsDB:

    # Use NAUTICAL depression for dawn calculation (sun 12 degrees below horizon)
    # because with default value CIVIL (6 degrees below horizon), time is too late,
    # it is already too bright
    DEFAULT_DEPRESSION: Union[float, astral.Depression] = astral.Depression.NAUTICAL    

    KEY_DAWN_CLOSE: str = "DAWN_CLOSE"
    KEY_OPEN_AT: str = "OPEN_AT"
    KEY_DEPRESSION: str = "DEPRESSION"
    KEY_LATEST: str = "LATEST"

    def __init__(self, filename: Path) -> None:
        self.__filename = filename

    def save(self, settings: ShutterSettings) -> None:
        """Write settings to persistent database file.

        The persistently stored settings can later be read using
        read_settings_from_db(). Note that that read_settings_from_db() function returns
        the settings in a format different to the arguments given to
        write_settings_to_db().

        Parameters:
            dawn_close (boolor None): one of:
                - 0 if shutters shall not be closed at dawn
                - != 0 if shutters shall be closed at dawn
                - None if persisted value shall not be changed
            open_at (str or None): one of:
                - Time in ISO format (e.g. "hh:mm", "hh:mm:ss", "hh:mm +0200")
                - 'off'
                - None if persisted value shall not be changed
            depression (float or astral.Depression or None): one of:
                - depression as astral.Depression enum object
                - depression as floating point number (degrees under horizon)
                - None if persisted value shall not be changed
            latest (str): one of:
                - Time in ISO format (e.g. "hh:mm", "hh:mm:ss", "hh:mm +0200")
                - 'off'
                - None if persisted value shall not be changed
        """
        dawn_close = settings.close_at_dawn
        open_at = settings.open_at_time
        depression = settings.depression
        latest = settings.latest

        with shelve.open(self.__filename) as db:
            # Convert and write dawn_close
            if dawn_close != None:
                db[self.KEY_DAWN_CLOSE] = False if dawn_close == 0 else True

            # Convert and write open_at
            if open_at != None:
                if open_at == 'off':
                    if self.KEY_OPEN_AT in db:
                        del db[self.KEY_OPEN_AT]
                else:
                    open_at_timeobj = datetime.time.fromisoformat(open_at)
                    db[self.KEY_OPEN_AT] = open_at_timeobj

            # Write depression
            if depression != None:
                db[self.KEY_DEPRESSION] = depression

            # Convert and write "latest"
            if latest != None:
                if latest == 'off':
                    del db[self.KEY_LATEST]
                else:
                    latest_timeobj = datetime.time.fromisoformat(latest)
                    db[self.KEY_LATEST] = latest_timeobj

    def load(self) -> ShutterSettings:
        """Read settings from persistent database file.

        Returns:
        Tuple of:
            - bool value indicating whether or not shutter shall be closed at dawn
            - datetime.time object indicating when shutters shall be opend, or None
            if shutters shall not be opened
            - depression object (astral.Depression) or float for depression
            - datetime.time object indicating when shutters shall be closed at
            the latest, even before dawn
        """        
        with shelve.open(self.__filename) as db:
            dawn_close = db.get(self.KEY_DAWN_CLOSE, True)
            open_at = db.get(self.KEY_OPEN_AT, None)
            depression = db.get(self.KEY_DEPRESSION, self.DEFAULT_DEPRESSION)
            latest = db.get(self.KEY_LATEST, None)

        return ShutterSettings(dawn_close, open_at, depression, latest)
