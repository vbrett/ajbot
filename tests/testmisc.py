'''
test misc stuff
'''
import sys
import asyncio

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from vbrpytools.misctools import divide_list

from ajbot._internal.ajdb import AjDb
# from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal.config import FormatTypes

async def _main():
    ''' main function - async version
    '''
    async with AjDb() as aj_db:
        members = await aj_db.query_members_per_season_presence()

    # sort alphabetically per last name / first name
    members.sort(key=lambda x: x.credential)

    # use Matplotlib to write to a PDF, creating a figure with only the data table showing up
    inch_to_cm = 2.54
    fig, ax = plt.subplots(figsize=(21/inch_to_cm, 29.7/inch_to_cm))  # A4 size in inches

    ax.axis('off')
    input_dic = [{'id': f'{member.id:{FormatTypes.FULLSIMPLE}}',
                  'Nom': f'{member.credential:{FormatTypes.FULLSIMPLE}}',
                  'presence': f'{member.current_season_not_subscriber_presence_count()}',
                  'signature': '',
                 } for member in members]

    input_list = [list(d.values()) for d in input_dic]
    input_columns = list(input_dic[0].keys())
    input_columns_width = [0.1, 0.3, 0.1, 0.5] # Need adjust if changing list of columns, total should always be 1

    row_per_page = 20
    table_height_scale = 2.7  # Need adjust if changing mbr_per_page

    # add empty rows to have full pages + one full blank page
    n_empty_rows = row_per_page - (((len(input_list) - 1) % row_per_page) + 1)
    n_empty_rows += row_per_page
    input_list += [['']*len(input_columns)]*n_empty_rows

    # Create the PDF and write the table to it, splited per page
    with PdfPages('./aj_xls2db/table.pdf') as pdf_pages:
        for sub_input_list in divide_list(input_list, row_per_page):
            _the_table = ax.table(
                cellText=sub_input_list,
                colLabels=input_columns,
                colWidths=input_columns_width,
                loc='center'
            )
            _the_table.scale(1, table_height_scale)

            pdf_pages.savefig(fig)

    return 0

if __name__ == '__main__':
    sys.exit(asyncio.run(_main()))
