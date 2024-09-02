# Kingroon

Complement for Octoprint.

This software is intended to work together with the electronic design

## Display

```

```

## States

| State | Description | Transitions |
|-------|-------------|-------------|
| `OFF`   | Printer is powered off | &rarr; `POWERON` |
| `POWERON` | Printer is powering on | When Octoprint is connected &rarr; `IDLE` |
| `IDLE` | Print is waiting | Start a job &rarr; `PRINTING` |
| `PRINTING` | Print job in progress | End or cancel job &rarr; `COOLING` |
| `COOLING` | Printer is cooling | Printer cold &rarr; `COLD` |
| `COLD` | Printer is cool | After beeping &rarr; `IDLE` |
| `CLOSED` | Door is closed | Treated as `OFF` with no transition allowed |

## User actions

- *Power* button turns printer on or off

    - `OFF` &rarr; `IDLE`

    - `IDLE`|`COOLING`|`COLD` &rarr; `OFF`

    - `PRINTING` &rarr; `COOLING` (cancels the job)

- *Flash* button toggles the camera flash, which is also synchronized with video capture

- *Light* button toogles the overhead light

- Touch sensor

    - Short touch toggles overhead light

    - Long touch acts like the *Power* button

## Display

| Top line | Description |
|----------|-------------|
| `Off` | Printer is powered off |
| `Operational` | Octoprint is ready, no job queued |
| *Job name* | Current or last print job if any |

## Events

- Events from CGI are passed through the file `/usr/share/octobox/socket`.

- Touch events are monitored by a dedicated thread and stored in Peripheral.longTouch

- Octoprint's state is read by the function `Octoprint.getState()`

    - `Offline` : printer is disconnected (probably off)

    - `Operational` : Octoprint is ready to print

    - `Printing` : print in progress

    - `Cancelling` : cancelling job

    - `Error`, others

## Sub-modules

### Octoprint (`octo_print.py`)

- `Octoprint.getTemps()` returns a tuple with the extruder's and the bed's temperature

- `Octoprint.getJobInfo()` returns a tuple with

    - the file name of the current job (queued or printing or ended)

    - elapsed print time

    - remaining print time (as estimated by Octoprint)

    - the estimated total time (from the file)

    - percentage done (as calculated by Octoprint)

### Display (`octo_disp.py`)

Uses `HD44780` (octo_lcd.py) to drive the LCD and also
writes files into `/var/www/html/` so that the Javascript in `index.html`
can pick it up and display it on the Web page.

| File | Content |
|------|---------|
| `localIP` | IP address for self |
| `state` | Text to be shown as title |
| `temps` | HTML to be shown as temperatures |
| `jobInfo` | HTML to be shown as Job information |

### Peripherals (`octo_periph.py`)

Drives the GPIO inputs and outputs.

| Function | Pin # | GPIO # | Method name |
|----------|-------|--------|-------------|
| Overhead light | 12 | 257 | `light()` |
| Camera flash | 36 | 76 | `flash()` |
| Fan | 38 | 260 | `fan()` |
| Relay output (power) | 40 | 259 | `relay()` |
| Reed input (door) | 16 | 270 | `doorClosed` |
| Touch input | 18 | 228 | `longTouch` |

- Short touch events (toggle overhead light) are processed directly by Peripheral.

- A long touch event sets `longTouch` to `True`.
The property must be reset to `False` when processing is done.

- The overhead light is synchronized with the display's backlight.

### Sound (`octo_sound.py`)

Call `Sound.start(id)` to generate the chime `id`.
`Sound.stop()` to stop it before it's finished.

| Name | Index | When | What |
|------|-------|------|------|
| STOP | 0 | Stop sound | Any time |
| TOUCH | 1 | Short touch beep | Short beep |
| TOUCHLG | 2 | Long touch beep | Long beep|
| OPEN | 3 | Door opening | Encounters of the Third Kind |
| CLOSE | 4 | Door closing | Beethoven's 5th |
| POWERON | 5 | Powering on | The Good, the Bad, and the Ugly |
| POWEROFF | 6 | Powering off | Every Breath You Take |
| START | 7 | Print starting | Star Trek |
| CANCEL | 8 | Cancelling print | Toccata & Fugue |
| COOLING | 9 | End of print | Let it go |
| COLD | 10 | Print cold | Beethoven's 9th |

### Camera (`octo_cam.py`)

Drive the Webcam on USB. Automatically detects the USB device.
Needs a Peripheral object to drive the flash.

- `start()` starts `ustreamer` on port 8080

- `stop()` stops it

- `capture()` make a snapshot and stores it in `/var/www/html/image.jpg`

### Web page (`index.html`)

Shows the current status of the printer, with [three buttons](#user-actions)
to control the state. It shows either a video stream (`\\host\stream`) if a job is in progress,
or a still capture (`image.jpg`) if not. The server's IP address is derived from the `localIP` file.
