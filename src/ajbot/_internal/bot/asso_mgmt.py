""" Function for asso management outputs (Views, buttons, message, ...)
"""
from datetime import datetime, timedelta
import tempfile
from pathlib import Path

from discord import Interaction, File as Dfile
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from vbrpytools.misctools import divide_list

from ajbot._internal.config import AjConfig, FormatTypes, AJ_SIGNSHEET_FILENAME
from ajbot._internal.ajdb import AjDb, tables as db_t
from ajbot._internal.bot import responses
from ajbot._internal.exceptions import OtherException



async def role_display(aj_config:AjConfig,
                       aj_db:AjDb,
                       interaction: Interaction):
    """ Affiche les infos des roles
    """
    if not interaction.response.type:
        await interaction.response.defer(ephemeral=True,)

    discord_role_mismatches = {}
    aj_members = await aj_db.query_table_content(db_t.Member, refresh_cache=True)
    aj_discord_roles = await aj_db.query_table_content(db_t.DiscordRole, refresh_cache=True)
    default_asso_role_id = aj_config.asso_member_default
    default_discord_role_ids = [dr.id for dr in aj_discord_roles if default_asso_role_id in [ar.id for ar in dr.asso_roles]]

    for discord_member in interaction.guild.members:
        actual_role_ids = [r.id for r in discord_member.roles if r.name != "@everyone"]

        matched_members = [d for d in aj_members if d.discord == discord_member.name]
        assert (len(matched_members) <= 1), f"Erreur dans la DB: Plusieurs membres correspondent au même pseudo Discord {discord_member}:\n{', '.join(m.name for m in matched_members)}"
        if len(matched_members) == 0:
            member = None
            # discord user not found in db, expected discord role is default
            expected_role_ids = default_discord_role_ids
        else:
            # discord user found in db, check using asso role
            member = matched_members[0]
            if (not member.is_subscriber
                and member.is_past_subscriber
                and (   not member.last_presence
                        or member.last_presence < (datetime.now().date() - timedelta(days = aj_config.asso_role_reset_duration_days)))):
                # user is a past subscriber but has not participated for some time, expected discord role is default
                expected_role_ids = default_discord_role_ids
            else:
                # expected discord role(s) are the ones mapped to user asso role
                expected_role_ids = [dr.id for dr in member.current_asso_role.discord_roles]

        expected_role_ids = set(expected_role_ids)
        actual_role_ids = set(actual_role_ids)
        if expected_role_ids != actual_role_ids:
            expected_role_key = '; '.join(f"{interaction.guild.get_role(id) or id}" for id in expected_role_ids)
            discord_role_mismatches.setdefault(expected_role_key, [])
            discord_role_mismatches[expected_role_key].append(  f"{member if member else discord_member.name} - "
                                                                + '; '.join(f"{interaction.guild.get_role(id) or id}" for id in actual_role_ids))

    if discord_role_mismatches:
        summary = "Des roles ne sont pas correctements attribués :"
        sep = '\n  - '
        reply = '\n'.join(f"- Attendu(s): {k}\n  - {sep.join(e for e in v)}" for k, v in discord_role_mismatches.items())
        # reply = '\n'.join(f"- {u['who']} :\n  - attendu(s): {u['expected']}\n  - actuel(s): {u['actual']}" for u in discord_role_mismatches)
    else:
        summary = "Parfait ! Tout le monde a le bon rôle !"
        reply = None

    await responses.send_response_as_view(interaction=interaction, title="Rôles", summary=summary, content=reply, ephemeral=True)


async def email_display(aj_db:AjDb,
                        subscriber_only:bool,
                        interaction: Interaction):
    """ Envoie la liste d'emails
    """
    if not interaction.response.type:
        await interaction.response.defer(ephemeral=True,)

    members = await aj_db.query_table_content(db_t.Member, refresh_cache=True)

    emails = [m.email_principal.email for m in members if     m.email_principal
                                                          and (   m.is_subscriber
                                                               or (    not subscriber_only
                                                                   and m.last_presence
                                                                   and m.last_presence >= (datetime.now().date() - timedelta(days=365))
                                                                  )
                                                              )]
    summary = "Cotisants cette saison" if subscriber_only else 'Personnes ayant participé au moins une fois au cours des 12 derniers mois'
    summary += f" - {len(emails)} email(s)"
    reply = ';'.join(f"{email:{FormatTypes.FULLCOMPLETE}}" for email in emails)

    await responses.send_response_as_view(interaction=interaction, title="Emails", summary=summary, content=reply, ephemeral=True)


async def sign_sheet_display(aj_config:AjConfig,
                             aj_db:AjDb,
                             interaction: Interaction):
    """ Crée et envoie la feuille de présence
    """
    if not interaction.response.type:
        await interaction.response.defer(ephemeral=True,)

    members = await aj_db.query_members_per_season_presence()
    free_venues = aj_config.asso_free_presence

    # sort alphabetically per last name / first name
    members.sort(key=lambda x: x.credential)

    # use Matplotlib to write to a PDF, creating a figure with only the data table showing up
    inch_to_cm = 2.54
    fig, ax = plt.subplots(figsize=(21/inch_to_cm, 29.7/inch_to_cm))  # A4 size in inches

    ax.axis('off')
    input_dic = [{'ID': f"{member.id:{FormatTypes.FULLSIMPLE}}",
                  'Nom': f"{member.credential:{FormatTypes.FULLSIMPLE}}",
                  '#': "" if member.is_subscriber else f"{'>' if member.season_presence_count() >= free_venues else ''}{member.season_presence_count()}",
                  'Signature': '',
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
    with tempfile.TemporaryDirectory() as temp_dir:
        sign_sheet_file = Path(temp_dir) / AJ_SIGNSHEET_FILENAME
        with PdfPages(sign_sheet_file) as signsheet_file:
            for sub_input_list in divide_list(input_list, row_per_page):
                _the_table = ax.table(
                    cellText=sub_input_list,
                    cellLoc='center',
                    colLabels=input_columns,
                    colWidths=input_columns_width,
                    loc='center',
                )
                _the_table.scale(1, table_height_scale)

                signsheet_file.savefig(fig)

        with open(sign_sheet_file, mode="rb") as signsheet_file:
            await responses.send_response_as_text(interaction=interaction,
                                                  content="Feuille de présence:",
                                                  file=Dfile(fp=signsheet_file, filename=AJ_SIGNSHEET_FILENAME),
                                                  ephemeral=True)

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
