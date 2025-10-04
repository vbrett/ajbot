"""
Test Google Drive API integration.
"""

from vbrpytools.exceltojson import ExcelWorkbook

from ajbot._internal.google_api import GoogleDrive
from ajbot._internal.config import AJ_DB_FILE_ID, AJ_TABLE_NAME_SUIVI, AJ_TABLE_NAME_ANNUAIRE

if __name__ == "__main__":
    gdrive = GoogleDrive()
    aj_file = gdrive.get_file(AJ_DB_FILE_ID)
    xls = ExcelWorkbook(aj_file)

    suivi = xls.dict_from_table(AJ_TABLE_NAME_SUIVI, with_ignored=True)
    annuaire = xls.dict_from_table(AJ_TABLE_NAME_ANNUAIRE, with_ignored=True)

    suivi_saison_en_cours = [v for v in suivi if v.get('#support', {}).get('saison_en_cours', 0) > 0]

    seances = [v["date"] for v in suivi_saison_en_cours if v["entree"]["categorie"].lower() == "présence"]
    derniere_seance = max(seances)
    print(f"Dernière séance: {derniere_seance} - {len([seance for seance in seances if seance == derniere_seance])} participants.")
