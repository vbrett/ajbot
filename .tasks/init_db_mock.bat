setlocal
echo off

echo (re)start db container
cd .\tests\db_mock
docker compose down
docker compose up -d
cd ..\..

SET AJ_CONFIG_FILE=.\tests\db_mock\env.json
echo (re)create db content
uv run aj_migrate .\tests\db_mock\db_mock.xlsx

endlocal