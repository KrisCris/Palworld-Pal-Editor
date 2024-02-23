# Create a virtual environment named 'venv' (skip if already created)
python -m venv venv

# Activate the virtual environment
. .\venv\Scripts\Activate.ps1

# Install packages from requirements.txt
pip install -r requirements.txt

# Install your package in editable mode
pip install -e .

# Run your package
python -m palworld_pal_editor