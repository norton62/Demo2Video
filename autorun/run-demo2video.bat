:: Demo2Video autorun script By Oesch.me for project https://github.com/norton62/Demo2Video
:: This bat-file can be moved to any location for conviniency.
:: It start required scripts in standalone terminal windows 
:: and automatically starts OBS + launches local webinterface

:: ---------------- Set these variables --------------------------
:: Change the paths to match your setup!
:: Use project root locations for d2v and csdm
:: OBS location is default installation location. Change if needed.

set csdmlocation=C:\path\to\cs-demo-manager
set d2vlocation=C:\path\to\Demo2Video
set obslocation="%ProgramFiles%\obs-studio\bin\64bit"

:: ----------------- End of variables ----------------------------



:: Modifying code under this line might cause faillure to start!
:: --------------------------------------------------------------
:: Navigate to CSDM project folder
cd %csdmlocation%
:: Start CSDM terminal
start "CLI" /min cmd /k node ./scripts/develop-cli.mjs
:: Navigate to OBS installation folder. 
cd %obslocation%
:: Start OBS Studio
start "OBSSTUDIO" %obslocation%\obs64.exe
::Navitate to D2V Foldder.
cd %d2vlocation%
:: Start the main runner
start "Py-Main" /min cmd /k python ./main.py
:: Open the web interface in default browser
start "" http://localhost:5001/