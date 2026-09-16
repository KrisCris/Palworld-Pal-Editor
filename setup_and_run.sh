if which npm > /dev/null; then
    NPM_CMD=npm
else
    echo "Node is not installed."
fi

cd "./frontend/palworld-pal-editor-webui"
${NPM_CMD} install
${NPM_CMD} run build
cd "../../"
rm -r "./src/palworld_pal_editor/webui"
mv "./frontend/palworld-pal-editor-webui/dist" "./src/palworld_pal_editor/webui"

# Check for Python 3.x and set the appropriate command
if which python3 > /dev/null; then
    PYTHON_CMD=python3
elif which python > /dev/null; then
    PYTHON_CMD=python
else
    echo "Python is not installed."
    exit 1
fi

# Extract the Python version
PYTHON_VERSION=$(${PYTHON_CMD} --version | awk '{print $2}')
PYTHON_MAJOR_VERSION=$(echo ${PYTHON_VERSION} | cut -d. -f1)
PYTHON_MINOR_VERSION=$(echo ${PYTHON_VERSION} | cut -d. -f2)

# Check if Python version is 3.11 or newer
if [ "${PYTHON_MAJOR_VERSION}" -lt 3 ] || { [ "${PYTHON_MAJOR_VERSION}" -eq 3 ] && [ "${PYTHON_MINOR_VERSION}" -lt 11 ]; }; then
    echo "Python version 3.11 or newer is required."
    exit 1
fi

echo "Using ${PYTHON_CMD} (version ${PYTHON_VERSION})"

${PYTHON_CMD} -m venv venv
VENV_PYTHON="./venv/bin/python"

"${VENV_PYTHON}" -m pip install -r requirements.txt

# The editor runs out of the source tree, so there is nothing to install for it
# -- `src` on PYTHONPATH is all an install was ever doing here.
export PYTHONPATH="$(pwd)/src"

echo "Launching python -m palworld_pal_editor ${@}..."
"${VENV_PYTHON}" -m palworld_pal_editor "${@}"
