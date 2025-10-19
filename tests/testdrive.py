"""
Test Google Drive API integration.
"""
from thefuzz import fuzz
from thefuzz import process
from vbrpytools.exceltojson import ExcelWorkbook

from ajbot._internal.google_api import GoogleDrive
from ajbot._internal.config import AjConfig

if __name__ == "__main__":
    with AjConfig(break_if_missing=True, save_on_exit=False) as aj_config:
        gdrive = GoogleDrive(aj_config)
        aj_file = gdrive.get_file(aj_config.file_id_db)
        xls = ExcelWorkbook(aj_file)

        suivi = xls.dict_from_table(aj_config.db_table_events, with_ignored=True)
        annuaire = xls.dict_from_table(aj_config.db_table_roster, with_ignored=True)

    suivi_saison_en_cours = [v for v in suivi if v.get('#support', {}).get('saison_en_cours', 0) > 0]

    seances = [v["date"] for v in suivi_saison_en_cours if v["entree"]["categorie"].lower() == "présence"]
    derniere_seance = max(seances)
    print(f"Dernière séance: {derniere_seance} - {len([seance for seance in seances if seance == derniere_seance])} participants.")

    SEARCH_NAME = "Falaschi Florian"
    choices = [member['nom_userfriendly'] for member in annuaire]
    process.extractBests(SEARCH_NAME, choices, 90)
    max(annuaire, key=lambda x:fuzz.token_sort_ratio("mouchet anges", x["nom_userfriendly"]))
