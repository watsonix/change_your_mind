cd ./Spacebrew/
taskkill /F /IM node.exe
taskkill /F /IM python.exe
start node node_server_forever.js 
timeout /t 1 /nobreak
start node node_server_forever.js -p 9002 &
timeout /t 1 /nobreak
cd ..
taskkill /F /IM wmplayer.exe
REM taskkill /F /IM chrome.exe
REM start "" "C:\Program Files (x86)\Windows Media Player\wmplayer.exe" "C:\Users\ExplorCogTech\Music\stream.wav"
start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --kiosk
timeout /t 1 /nobreak
REM activate py3
REM timeout /t 3 /nobreak
start runmain.bat