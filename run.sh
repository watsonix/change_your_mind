#!/bin/bash
cd ./Spacebrew-spacebrew-672a874/
killall python	
killall node
sleep 1
node node_server_forever.js &
sleep 1
node node_server_forever.js -p 9002 &
sleep 1
cd ..
python ./main.py 
