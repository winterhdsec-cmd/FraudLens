@echo off
title FraudLens Docker Stop

echo Stopping FraudLens...
docker-compose down
echo.
echo All services stopped.
pause
