import argparse
import sys
import shelve
import datetime
import os
import astral
import astral.sun
import time
import dataclasses
import RPi.GPIO as GPIO
from typing import Union


LOCATION_CITY: str = 'Stuttgart'
LOCATION_REGION: str = 'Germany'
LOCATION_TIMEZONE: str = 'Europe/Berlin'
LOCATION_LATITUDE: float = 48.7684
LOCATION_LONGITUDE: float = 9.1903

# Use NAUTICAL depression for dawn calculation (sun 12 degrees below horizon)
# because with default value CIVIL (6 degrees below horizon), time is too late,
# it is already too bright
DEFAULT_DEPRESSION: Union[float, astral.Depression] = astral.Depression.NAUTICAL

PERSISTENCE_FILENAME: str = os.path.expanduser('~/.shutterControlShelve.db')
KEY_DAWN_CLOSE: str = "DAWN_CLOSE"
KEY_OPEN_AT: str = "OPEN_AT"
KEY_DEPRESSION: str = "DEPRESSION"
KEY_LATEST: str = "LATEST"

GPIO_BOARD_PIN_OPEN:  int = 16
GPIO_BOARD_PIN_CLOSE: int = 18

GPIO_ACTUATION_DURATION_SECONDS: float = 0.3


@dataclasses.dataclass
class Event:
	open: bool
	time: datetime.datetime


@dataclasses.dataclass
class Settings:
	close_at_dawn: bool
	open_at_time:  Union[None, datetime.time]
	depression:    Union[float, astral.Depression]
	latest:        Union[None, datetime.time]


def kill_other_tasks():
	scriptname = os.path.basename(__file__)
	regexp = 'python.*[' + scriptname[0] + ']' + scriptname[1:]
	os.system(f"kill $(ps axf | grep '{regexp}' | grep --invert-match {os.getpid()} | awk '{{print $1'\}})")


def write_settings_to_db(
	dawn_close: Union [None, bool],
	open_at: Union[None, str],
	depression: Union[None, float, astral.Depression],
	latest:     Union[None, str] = None) -> None:
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
	with shelve.open(PERSISTENCE_FILENAME) as shelf:
		# Convert and write dawn_close
		if dawn_close != None:
			shelf[KEY_DAWN_CLOSE] = False if dawn_close == 0 else True

		# Convert and write open_at
		if open_at != None:
			if open_at == 'off':
				if KEY_OPEN_AT in shelf:
					del shelf[KEY_OPEN_AT]
			else:
				open_at_timeobj = datetime.time.fromisoformat(open_at)
				shelf[KEY_OPEN_AT] = open_at_timeobj

		# Write depression
		if depression != None:
			shelf[KEY_DEPRESSION] = depression

		# Convert and write "latest"
		if latest != None:
			if latest == 'off':
				del shelf[KEY_LATEST]
			else:
				latest_timeobj = datetime.time.fromisoformat(latest)
				shelf[KEY_LATEST] = latest_timeobj


def read_settings_from_db() -> Settings:
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
	with shelve.open(PERSISTENCE_FILENAME) as shelf:
		dawn_close_bool = shelf.get(KEY_DAWN_CLOSE, True)
		open_at_timeobj = shelf.get(KEY_OPEN_AT, None)
		depression = shelf.get(KEY_DEPRESSION, DEFAULT_DEPRESSION)
		latest = shelf.get(KEY_LATEST, None)

		return Settings(dawn_close_bool, open_at_timeobj, depression, latest)


def calc_dawn_time(date: datetime.date,
		depression: Union[float, astral.Depression]) -> datetime.datetime:

	loc = astral.LocationInfo(LOCATION_CITY, LOCATION_REGION, LOCATION_TIMEZONE,
		LOCATION_LATITUDE, LOCATION_LONGITUDE
	)
	dawntime = astral.sun.dawn(loc.observer, date, tzinfo=loc.timezone,
		depression=depression)
	return dawntime


def earlier_time(date_time: datetime.datetime, latest_time: datetime.time) -> datetime.datetime:
	"""Determine combined earlier datetime

	If latest_time is None, or if latest_time is a time which is later than the
	time of date_time, just returns the unchanged date_time.
	If latest_time is earlier than the time of date_time, replaces the time
	in date_time with latest_time and returns it.

	Parameters:
		date_time: date and time, which must be offset-aware
		latest_time: time which can be offset-naive, or None
	"""
	if latest_time != None:
		latest_datetime = datetime.datetime.combine(date_time, latest_time,
			tzinfo=date_time.tzinfo)
		return min(date_time, latest_datetime)
	else:
		return date_time


def determine_next_event(settings: Settings) -> Event:
	"""Determines next event, i.e. when to open or close shutters.

	If open_at time is before dawn time for a particular day, dawn time will be
	ignored, i.e. shutters will open at open_at time, but not close anymore at
	dawn time.

	Parameters:
		dawn_close_bool (bool): Whether or not closing and dawn shall be taken into account
		open_at_timeobj (datetime.time): Time when shutters shall be opened, or None if not
		depression (astral.Depression or float)
		latest (datetime.time): Time to close, even before dawn

	Returns:
		Tuple of:
			bool value indicating whether shutters shall be opened (True) or closed (False)
			int value indicating seconds from now when event shall be triggered
				or -1 if no event to be triggered
	"""
	now = datetime.datetime.now(datetime.timezone.utc)
	today = datetime.date.today()
	tomorrow = today + datetime.timedelta(days=1)

	open_at = None
	keep_open_for_today = False
	if settings.open_at_time != None:
		open_at = datetime.datetime.combine(today, settings.open_at_time).astimezone()
		if open_at < now:
			open_at = datetime.datetime.combine(tomorrow, settings.open_at_time).astimezone()
			keep_open_for_today = True

	close_at = None
	if settings.close_at_dawn:
		dawntime_today = calc_dawn_time(today, settings.depression)
		close_at = earlier_time(dawntime_today, settings.latest)
		if close_at < now or keep_open_for_today:
			dawntime_tomorrow = calc_dawn_time(tomorrow, settings.depression)
			close_at = earlier_time(dawntime_tomorrow, settings.latest)

	if open_at == None:
		if close_at == None:
			return None
		else:
			return Event(False, close_at)
	elif close_at == None or open_at < close_at:
		return Event(True, open_at)
	else:
		return Event(False, close_at)


def init_gpio() -> None:
	GPIO.setmode(GPIO.BOARD)
	GPIO.setwarnings(False)
	GPIO.setup (GPIO_BOARD_PIN_OPEN, GPIO.OUT)
	GPIO.output(GPIO_BOARD_PIN_OPEN, GPIO.HIGH)
	GPIO.setup (GPIO_BOARD_PIN_CLOSE, GPIO.OUT)
	GPIO.output(GPIO_BOARD_PIN_CLOSE, GPIO.HIGH)


def actuate_shutters(open: bool) -> None:
	pin_to_actuate = GPIO_BOARD_PIN_OPEN if open else GPIO_BOARD_PIN_CLOSE
	GPIO.output(pin_to_actuate, GPIO.LOW)
	time.sleep(GPIO_ACTUATION_DURATION_SECONDS)
	GPIO.output(pin_to_actuate, GPIO.HIGH)


def main(dawn_close: int, open_at: str) -> int:
	# Kill any already running tasks which are running this very script
	kill_other_tasks()

	# Initialize GPIO pins
	init_gpio()

	# Write settings to database (if given as arguments)
	write_settings_to_db(dawn_close, open_at)

	# Read settings from database (Note: will be returned in different format)
	dawn_close_bool, open_at_timeobj = read_settings_from_db()
	print(f'{dawn_close_bool=}, {open_at_timeobj=}')

	while True:
		# Calculate when next shutters up or shutters down event shall occur
		next_event = determine_next_event(dawn_close_bool, open_at_timeobj)
		if next_event != None and next_event.time != None:
			print(f'{next_event=}')

			# Wait until next event is due
			time.sleep((next_event.time - datetime.datetime.now()).total_seconds())

			# Actuate shutters accordingly
			actuate_shutters(open)

		else:
			print('No next event determined, nothing to be done. Exiting.')


if __name__ == '__main__':
	parser = argparse.ArgumentParser(
		description='Somfy shutter day dawn and morning alarm control'
	)
	parser.add_argument('-d', '--dawn-close', type=int, metavar='(1|0)',
		help='Whether shutters shall be closed when day dawns (--dawn 1) or not (--dawn 0)')
	parser.add_argument('-o', '--open-at', metavar='(<hh:mm>|off)',
		help='Time when shutters shall be opened (--open-at <hh:mm>) or not at all (--open-at off)')
	args = parser.parse_args()

	sys.exit(main(args.dawn_close, args.open_at))
