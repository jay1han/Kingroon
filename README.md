# Kingroon

Complement for Octoprint.

This software is intended to work together with the electronic design

## Display

```

```

## States

| State | Description | Transitions |
|-------|-------------|-------------|
| `OFF`   | Printer is powered off | Long-press button to power on |
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

- *Flash* button toggles the camera flash

- *Light* button toogles the overhead light

- Touch sensor

    - Short touch toggles overhead light

    - Long touch turns printer on or off

## Display

| Top line | Description |
|----------|-------------|
| `Off` | Printer is powered off |
| `Operational` | Octoprint is ready, no job queued |
| *Job name* | Printing or cooling or cold, shows the last print job if any |

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
| Overhead light | XX | 257 | `light()` |
| Camera flash | XX | 76 | `flash()` |
| Fan | XX | 260 | `fan()` |
| Relay output (power) | XX | 259 | `relay()` |
| Reed input (door) | XX | 270 | `doorClosed` |
| Touch input | XX 228 | `longTouch` |

- Short touch events (toggle overhead light) are processed directly by Peripheral.

- A long touch event sets `longTouch` to `True`.
The property must be reset to `False` when processing is done.

### Sound (`octo_sound.py`)

Call `Sound.start(id)` to generate the chime `id`

```
    STOP     = 0
    TOUCH    = 1      # 1 short beep
    TOUCHLG  = 2      # 3 short beeps and one long
    OPEN     = 3      # Encounters : A+B+GG-D
    CLOSE    = 4      # Beethoven 5 : GGGEb
    POWERON  = 5      # Leone : C#F#C#F#C#
    POWEROFF = 6      # Every Breath You Take : CDCBA
    START    = 7      # Star Trek : BEA+G#
    CANCEL   = 8      # Toccata & Fugue : A+GA+
    COOLING  = 9      # Let it go : FGA+bC
    COLD     = 10     # Ode a la joie : BBCD
```

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
