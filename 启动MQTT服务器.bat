@echo off
:: Start EMQX MQTT server
echo ���� EMQX MQTT ������...

:: Set EMQX installation path
set EMQX_PATH=.\emqx-5.3.0-windows-amd64\bin


:: Start EMQX
call %EMQX_PATH%\emqx start
echo EMQX MQTT ������������.

:: Pause to view output, press any key to continue
pause