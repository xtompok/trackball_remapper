#!/usr/bin/env python3

import evdev
from evdev import ecodes,AbsInfo,UInput

def print_capabilities(device):
    capabilities = device.capabilities(verbose=True)

    print('Device name: {.name}'.format(device))
    print('Device info: {.info}'.format(device))

    if ('EV_LED', ecodes.EV_LED) in capabilities:
        leds = ','.join(i[0] for i in device.leds(True))
        print('Active LEDs: %s' % leds)

    active_keys = ','.join(k[0] for k in device.active_keys(True))
    print('Active keys: %s\n' % active_keys)

    print('Device capabilities:')
    for type, codes in capabilities.items():
        print('  Type {} {}:'.format(*type))
        for code in codes:
            # code <- ('BTN_RIGHT', 273) or (['BTN_LEFT', 'BTN_MOUSE'], 272)
            if isinstance(code[1], AbsInfo):
                print('    Code {:<4} {}:'.format(*code[0]))
                print('      {}'.format(code[1]))
            else:
                # Multiple names may resolve to one value.
                s = ', '.join(code[0]) if isinstance(code[0], list) else code[0]
                print('    Code {:<4} {}'.format(s, code[1]))
        print('')


devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

trackball = None

for dev in devices:
	if "Logitech USB Trackball" in dev.name:
		trackball = dev
		break

if trackball is None:
	print("No trackball found, exitting")
	exit(1)

print_capabilities(trackball)
trackball.grab()
trackball_cap = trackball.capabilities()
capabilities = trackball.capabilities()
del capabilities[ecodes.EV_SYN] # Without this it fails 
capabilities[ecodes.EV_REL].append(ecodes.REL_HWHEEL)
capabilities[ecodes.EV_REL].append(ecodes.REL_WHEEL)
capabilities[ecodes.EV_REL].append(ecodes.REL_HWHEEL_HI_RES)
capabilities[ecodes.EV_REL].append(ecodes.REL_WHEEL_HI_RES)
out = UInput(events=capabilities, name='Trackball remapped')
print(out.capabilities(verbose=True))

WHEEL_THRESHOLD = 5
HWHEEL_THRESHOLD = 5

scrolling = False
scrolled = False
mem_down = None
wheel_accum = 0
hwheel_accum = 0
for event in trackball.read_loop():
	print(evdev.categorize(event))
	match event.type:
		case ecodes.EV_SYN:
			print("Sync")
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
			print("Key")
			pass
		case ecodes.EV_REL:
			print("Rel")
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
			print("Msc")
			out.write_event(event)
#	out.syn()
