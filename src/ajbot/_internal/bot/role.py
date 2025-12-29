""" Function roles outputs (Views, buttons, message, ...)
"""
from datetime import datetime, timedelta

from discord import Interaction

from ajbot._internal.config import AjConfig
from ajbot._internal.ajdb import AjDb, tables as db_t
from ajbot._internal.bot import responses
from ajbot._internal.exceptions import OtherException

async def display(aj_config:AjConfig,
                  aj_db:AjDb,
                  interaction: Interaction):
    """ Affiche les infos des roles
    """
    if not interaction.response.type:
        await interaction.response.defer(ephemeral=True,)

    discord_role_mismatches = {}
    aj_members = await aj_db.query_table_content(db_t.Member)
    aj_discord_roles = await aj_db.query_table_content(db_t.DiscordRole)
    default_asso_role_id = aj_config.asso_member_default
    default_discord_role_ids = [dr.id for dr in aj_discord_roles if default_asso_role_id in [ar.id for ar in dr.asso_roles]]

    for discord_member in interaction.guild.members:
        actual_role_ids = [r.id for r in discord_member.roles if r.name != "@everyone"]

        matched_members = [d for d in aj_members if d.discord_pseudo and d.discord_pseudo.name == discord_member.name]
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
        reply = '\n'.join(f"- Attendu(s): {k}\n  - {'\n  - '.join(e for e in v)}" for k, v in discord_role_mismatches.items())
        # reply = '\n'.join(f"- {u['who']} :\n  - attendu(s): {u['expected']}\n  - actuel(s): {u['actual']}" for u in discord_role_mismatches)
    else:
        summary = "Parfait ! Tout le monde a le bon rôle !"
        reply = None

    await responses.send_response_as_view(interaction=interaction, title="Rôles", summary=summary, content=reply, ephemeral=True)

if __name__ == '__main__':
    raise OtherException('This module is not meant to be executed directly.')
