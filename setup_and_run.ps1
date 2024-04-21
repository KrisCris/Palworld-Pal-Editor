# Function to check and return the available Python command
function Get-PythonCommand {
    $commands = @('python3', 'python')
    foreach ($cmd in $commands) {
        $version = & $cmd --version 2>&1
        if ($version -match "Python 3.") {
            return $cmd
        }
    }
    Write-Host "Python 3 is not installed."
    exit
}


# Check if npm is available
$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($null -ne $npmCmd) {
    $NPM_CMD = "npm"
} else {
    Write-Host "Node is not installed."
    Exit 1
}

# Install dependencies and build the project
cd ".\frontend\palworld-pal-editor-webui"
& $NPM_CMD install
& $NPM_CMD run build

cd "..\..\"
# Move the build directory
Remove-Item ".\src\palworld_pal_editor\webui" -Recurse -Force
New-Item -Path ".\src\palworld_pal_editor\webui" -ItemType "directory"
Move-Item -Path ".\frontend\palworld-pal-editor-webui\dist\*" -Destination ".\src\palworld_pal_editor\webui" -Force


# Determine the appropriate Python command
$PYTHON_CMD = Get-PythonCommand

# Check Python version
$versionOutput = & $PYTHON_CMD --version 2>&1
$versionNumbers = $versionOutput -replace "Python ", "" -split "\."
$majorVersion = [int]$versionNumbers[0]
$minorVersion = [int]$versionNumbers[1]

# Ensure Python version is at least 3.11
if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 11)) {
    Write-Host "Python version 3.11 or newer is required."
    exit
}

Write-Host "Using $($PYTHON_CMD) (version $($majorVersion).$($minorVersion))"

# Create and activate virtual environment
& $PYTHON_CMD -m venv venv
. .\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Install your package in editable mode
pip install -e .

# Run your package in interactive mode
python -m palworld_pal_editor $args
