from __future__ import annotations

from utils.resourceloader import ResourceLoader


class ConfigBot:
    
    def __init__(self, config: Config) -> None:
        self.__token: str = config['BOT']['token']
        self.__admin: str = config['BOT']['admin']

    @property
    def token(self) -> str:
        return self.__token

    @property
    def admin(self) -> str:
        return self.__admin

    def is_admin(self, user: str) -> bool:
        return user == self.__admin


class ConfigLocation:

    def __init__(self, config: Config) -> None:
        self.name: str = config["LOCATION"]['name']
        self.region: str = config["LOCATION"]['region']
        self.timezone: str = config["LOCATION"]['timezone']
        self.latitude: float = config["LOCATION"]['latitude']
        self.longitude: float = config["LOCATION"]['longitude']

    @property
    def name(self) -> str:
        return self.name

    @property
    def region(self) -> str:
        return self.region

    @property
    def timezone(self) -> str:
        return self.timezone

    @property
    def latitude(self) -> str:
        return self.latitude

    @property
    def longitude(self) -> str:
        return self.longitude


class ConfigGPIO:

    def __init__(self, config: Config) -> None:
        self.__pin_close: int = config['GPIO']['close']
        self.__pin_open: int = config['GPIO']['open']
        self.__actuation_duration: float = config['GPIO']['actuation_duration']

    @property
    def pin_open(self) -> int:
        return self.__pin_open

    @property
    def pin_close(self) -> int:
        return self.__pin_close

    @property
    def actuation_duration(self) -> float:
        return self.__actuation_duration


class ConfigDatabase:

    def __init__(self, config: Config) -> None:
        self.__filename = config['DATABASE']['filename']

    @property
    def filename(self) -> str:
        return self.__filename


class Config:

    def __init__(self) -> None:
        config = ResourceLoader.load_config()
        
        self.__bot = ConfigBot(config)
        self.__location = ConfigLocation(config)
        self.__gpio = ConfigGPIO(config)
        self.__db = ConfigDatabase(config)

    @property
    def bot(self) -> ConfigBot:
        return self.__bot

    @property
    def location(self) -> ConfigLocation:
        return self.__location

    @property
    def gpio(self) -> ConfigGPIO:
        return self.__gpio

    @property
    def db(self) -> ConfigDatabase:
        return self.__db
