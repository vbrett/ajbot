setlocal
echo off
@REM FOR /F "tokens=*" %%i in ("version.ini") do SET %%i
for /F "tokens=1,* eol=# delims== " %%i in (src/ajbot/resources/info.ini) do set %%i=%%~j

echo "building: %docker_tag%:%version%"

docker build --platform=linux/arm/v7,linux/amd64  --tag=%docker_tag%:%version% --push --no-cache .
docker build --platform=linux/arm/v7,linux/amd64  --tag=%docker_tag%:latest --push .
endlocal