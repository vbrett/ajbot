setlocal
@REM FOR /F "tokens=*" %%i in ("version.ini") do SET %%i
for /F "delims== tokens=1,* eol=#" %%i in (info.ini) do set %%i=%%~j

echo "building: %docker_tag%:%version%"

docker build --platform=linux/arm/v7  --tag=%docker_tag%:%version% --push .
docker build --platform=linux/arm/v7  --tag=%docker_tag%:latest --push .
docker build --platform=linux/amd64  --tag=%docker_tag%:%version% --push .
docker build --platform=linux/amd64  --tag=%docker_tag%:latest --push .
docker build --platform=linux/arm64  --tag=%docker_tag%:%version% --push .
docker build --platform=linux/arm64  --tag=%docker_tag%:latest --push .
endlocal