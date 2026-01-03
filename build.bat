setlocal
@REM FOR /F "tokens=*" %%i in ("version.ini") do SET %%i
for /F "delims== tokens=1,* eol=#" %%i in (src/ajbot/resources/info.ini) do set %%i=%%~j

echo "building: %docker_tag%:%version%"

docker build --platform=linux/arm/v7,linux/amd64  --tag=%docker_tag%:%version% --push .
docker build --platform=linux/arm/v7,linux/amd64  --tag=%docker_tag%:latest --push .
endlocal