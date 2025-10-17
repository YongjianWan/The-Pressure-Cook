Remember to run calibrate.py in order to determine input and output indexes. Assuming you have all modules installed just activate the environment and run the last command with the appropiatte indexes

```bash
# 1) Create & activate venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip

# 2) Install deps
python3 -m pip install -r requirements.txt
python3 -m pip install numpy pyserial opencv-python sounddevice


python3 microphone_visual_mergev2.py --in 2 --sr 44100 --in-channel 0 --print-audio --trig-db -10 --rel-db -14 --hold-sec 0.5

```