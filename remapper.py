#!/usr/bin/env python3

import argparse
import logging
import time
from collections.abc import Sequence
from typing import cast
import evdev
from evdev import ecodes,AbsInfo,UInput

logger = logging.getLogger(__name__)


def parse_args():
	parser = argparse.ArgumentParser(description='Logitech Trackball remapper')
	parser.add_argument(
		'--debug',
		action='store_true',
		help='Enable verbose debug logging'
	)
	return parser.parse_args()

def print_capabilities(device):
	capabilities = device.capabilities(verbose=True)

	logger.info('Device name: %s', device.name)
	logger.info('Device info: %s', device.info)

	if ('EV_LED', ecodes.EV_LED) in capabilities:
		leds = ','.join(i[0] for i in device.leds(True))
		logger.info('Active LEDs: %s', leds)

	active_keys = ','.join(k[0] for k in device.active_keys(True))
	logger.info('Active keys: %s', active_keys)

	logger.info('Device capabilities:')
	for type, codes in capabilities.items():
		logger.info('  Type %s %s:', *type)
		for code in codes:
			# code <- ('BTN_RIGHT', 273) or (['BTN_LEFT', 'BTN_MOUSE'], 272)
			if isinstance(code[1], AbsInfo):
				logger.info('    Code %-4s %s:', *code[0])
				logger.info('      %s', code[1])
			else:
				# Multiple names may resolve to one value.
				s = ', '.join(code[0]) if isinstance(code[0], list) else code[0]
				logger.info('    Code %s %s', s, code[1])


def find_trackball():
	devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

	trackball = None

	for dev in devices:
		logger.debug('%s', dev)
		if "Logitech USB Trackball" in dev.name:
			trackball = dev
			break

	if trackball is None:
		logger.warning('No trackball found')
		return (None,None)

	print_capabilities(trackball)
	trackball.grab()
	trackball_cap = trackball.capabilities()
	capabilities = trackball.capabilities()
	del capabilities[ecodes.EV_SYN] # Without this it fails 
	if ecodes.REL_HWHEEL not in capabilities[ecodes.EV_REL]:
		capabilities[ecodes.EV_REL].append(ecodes.REL_HWHEEL)
	if ecodes.REL_WHEEL not in capabilities[ecodes.EV_REL]:
		capabilities[ecodes.EV_REL].append(ecodes.REL_WHEEL)
	uinput_events = cast(dict[int, Sequence[int]], capabilities)
	out = UInput(events=uinput_events, name='Trackball remapped')
	logger.debug('%s', out.capabilities(verbose=True))
	return (trackball, out)

def event_loop(trackball,out): 
	WHEEL_THRESHOLD = 5
	HWHEEL_THRESHOLD = 5

	scrolling = False
	scrolled = False
	mem_down = None
	wheel_accum = 0
	hwheel_accum = 0
	for event in trackball.read_loop():
		logger.debug('%s', evdev.categorize(event))
		match event.type:
			case ecodes.EV_SYN:
				logger.debug('Sync')
				out.write_event(event)
			case ecodes.EV_KEY:
				match event.code:
					case ecodes.BTN_RIGHT:
						event.code = ecodes.BTN_LEFT
						out.write_event(event)
					case ecodes.BTN_LEFT:
						event.code = ecodes.BTN_RIGHT
						out.write_event(event)
					case ecodes.BTN_SIDE:
						out.write_event(event)
					case ecodes.BTN_EXTRA:
						event.code = ecodes.BTN_MIDDLE
						if event.value == 1: # Pressed
							scrolling = True
							mem_down = event
						elif event.value == 0:
							scrolling = False
							if not scrolled:
								if mem_down is not None:
									out.write_event(mem_down)
									out.syn()
									mem_down = None
								out.write_event(event)
							scrolled = False
				logger.debug('Key')
				pass
			case ecodes.EV_REL:
				logger.debug('Rel')
				if not scrolling:
					out.write_event(event)
				else:
					scrolled = True
					if event.code == ecodes.REL_X:
						hwheel_accum += event.value
						if abs(hwheel_accum) > HWHEEL_THRESHOLD:
							event.code = ecodes.REL_HWHEEL
							event.value = (hwheel_accum//HWHEEL_THRESHOLD)
							hwheel_accum %= HWHEEL_THRESHOLD
							out.write_event(event)
					elif event.code == ecodes.REL_Y:
						wheel_accum += event.value
						if abs(wheel_accum) > WHEEL_THRESHOLD:
							event.code = ecodes.REL_WHEEL
							event.value = -(wheel_accum//WHEEL_THRESHOLD)
							wheel_accum %= WHEEL_THRESHOLD
							out.write_event(event)

			case ecodes.EV_MSC:
				logger.debug('Msc')
				out.write_event(event)
	#	out.syn()

if __name__ == "__main__":
	args = parse_args()
	logging.basicConfig(
		level=logging.DEBUG if args.debug else logging.INFO,
		format='%(asctime)s %(levelname)s %(name)s: %(message)s'
	)
	while True:
		trackball, out = find_trackball()
		if trackball is not None and out is not None:
			try:
				event_loop(trackball, out)
			except OSError as e:
				logger.error('%s', e)
		time.sleep(3)
