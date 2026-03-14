setlocal
echo off

echo use migrate.json
SET AJ_CONFIG_FILE=.\.env\migrate.json
echo (re)create db content
uv run aj_migrate "G:/.shortcut-targets-by-id/1Vx6yXZmb9fp5sSD3bUuc9zIJx49oNmRT/dossier-maitre-assaut-des-jeux/Annuaire & Suivi.xlsx"

endlocal