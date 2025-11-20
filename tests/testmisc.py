'''
test mmis stuff
'''
import sys
import asyncio

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from ajbot._internal.ajdb import AjDb
# from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal.config import FormatTypes

async def _main():
    """ main function - async version
    """
    async with AjDb() as aj_db:
        members = await aj_db.query_season_members()

    members.sort(key=lambda x: x.credential)
    df = pd.DataFrame([{"id": f"{member.id:{FormatTypes.FULLSIMPLE}}",
                        "Nom": f"{member.credential:{FormatTypes.FULLSIMPLE}}",
                        "presence": f"{member.season_current_presence_count_check()}",
                        "roles": f"{', '.join([m.name for m in member.current_season_asso_roles if m])}",
                        "signature": "",
                       } for member in members])

    # Manipulate your dataframe 'df' here as required.

    # Now use Matplotlib to write to a PDF

    # Lets create a figure first
    fig, ax = plt.subplots(figsize=(20, 10))

    ax.axis('off')


    _the_table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        loc='center'
    )

    fig.show()
    # Now lets create the PDF and write the table to it
    pdf_pages = PdfPages("./aj_xls2db/table.pdf")
    pdf_pages.savefig(fig)
    pdf_pages.close()
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
