@echo off
:: Start EMQX MQTT server

:: Set EMQX installation path
set EMQX_PATH=.\emqx-5.3.0-windows-amd64\bin


:: Start EMQX
call %EMQX_PATH%\emqx start

:: Pause to view output, press any key to continue
pause