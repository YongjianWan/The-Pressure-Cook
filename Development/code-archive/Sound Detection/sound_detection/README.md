# Sound Detection Alarm (Python-only)

Monitors room loudness from an audio interface mic and plays an alarm on laptop speakers.

## Setup
```bash
cd Stir-Wars/Sound Detection/sound_detection
python3 -m venv .venv && source .venv/bin/activate  # Windows: venv\Scripts\activate. 
# Essentially create your own virtual environment. Replace .venv with your preferred environment name
# then activate the virtual environment with source .venv/bin/activate as you see above. Again remember to replace .venv with your name.
pip install -r requirements.txt