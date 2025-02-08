@echo off
set CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
set USER_DATA_DIR="C:\Users\astrowidow\AppData\Local\Google\Chrome\User Data\Default"

start "" %CHROME_PATH% --remote-debugging-port=9222 --user-data-dir=%USER_DATA_DIR% --profile-directory="Default" --disable-blink-features=AutomationControlled --disable-features=AutomationControlled