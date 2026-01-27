setlocal
echo off

echo (re)start db container
cd .\tests\db_test
docker compose down
docker compose up -d
cd ..\..

SET AJ_CONFIG_FILE=.\tests\db_test\env.json
echo (re)create db content
uv run aj_migrate .\tests\db_test\db_test.xlsx

endlocal