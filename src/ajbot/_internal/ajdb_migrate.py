""" test deployment of a MariaDB instance
"""
import sys
import asyncio
from datetime import datetime
from pathlib import Path

from vbrpytools.dicjsontools import load_json_file

from ajbot._internal import ajdb
from ajbot._internal.ajdb import AjDb


async def _create_db_schema(aj_db:AjDb):
    """ Drop and recreate db schema
    """
    await aj_db.drop_create_schema()


async def _populate_lut_tables(aj_db:AjDb):
    """ Populate lookup tables
    """
    try:
        xsldb_lookup_tables = load_json_file(Path('aj_xls2db/xlsdb_LUP.json'))
    except FileNotFoundError:
        return None

    lut_tables = []
    for val in xsldb_lookup_tables['saisons']:
        lut_tables.append(ajdb.Seasons(name=val['nom'],
                                    start=datetime.fromisoformat(val['debut']).date(),
                                    end=datetime.fromisoformat(val['fin']).date()))
    for val in xsldb_lookup_tables['contribution']:
        lut_tables.append(ajdb.LUTContribution(name=val['val']))
    for val in xsldb_lookup_tables['connaissance']:
        lut_tables.append(ajdb.LUTKnowFrom(name=val['val']))
    for val in xsldb_lookup_tables['compte']:
        lut_tables.append(ajdb.LUTAccounts(name=val['val']))
    for val in xsldb_lookup_tables['type_voie']:
        lut_tables.append(ajdb.LUTStreetTypes(name=val['val']))

    for val in xsldb_lookup_tables['discord_role']:
        lut_tables.append(ajdb.DiscordRoles(name=val['val'], id=int(val['id']),))
    for val in xsldb_lookup_tables['roles']:
        new_asso_role = ajdb.AssoRoles(name=val['asso'])
        lut_tables.append(new_asso_role)
        if val.get('discord'):
            for d_role in val['discord'].split(','):
                matched_role = [elt for elt in lut_tables
                                if isinstance(elt, ajdb.DiscordRoles) and elt.name == d_role]
                lut_tables.append(ajdb.JCTAssoDiscordRole(asso_role=new_asso_role,
                                                          discord_role=matched_role[0]))

    async with aj_db.AsyncSessionMaker() as session:
        async with session.begin():
            session.add_all(lut_tables)

    return lut_tables


async def _populate_member_tables(aj_db:AjDb, lut_tables):
    """ Populate member tables
    """
    try:
        xsldb_lut_member = load_json_file(Path('aj_xls2db/xlsdb_membres.json'))
    except FileNotFoundError:
        return None

    member_tables = []
    for val in xsldb_lut_member['annuaire']:
        try:
            _creation_date = datetime.fromisoformat(val['creation']['date'])
        except ValueError:
            continue
        new_member = ajdb.Members()
        member_tables.append(new_member)

        new_member.id=int(val['id'])

        if val.get('pseudo_discord'):
            new_member.discord_pseudo=ajdb.DiscordPseudos(name=val['pseudo_discord'])

        if val.get('prenom') or val.get('nom') or val.get('date_naissance'):
            new_member.credential = ajdb.MemberCredentials()
            new_member.credential.first_name=val.get('prenom')
            new_member.credential.last_name=val.get('nom')
            if val.get('date_naissance'):
                new_member.credential.birthdate = datetime.fromisoformat(val['date_naissance']).date()

        if val.get('emails'):
            principal = True
            for single_rpg in val['emails'].split(';'):
                matched_rpg = [elt for elt in member_tables
                            if isinstance(elt, ajdb.MemberEmails) and elt.address == single_rpg]
                if matched_rpg:
                    new_rpg = matched_rpg[0]
                else:
                    new_rpg = ajdb.MemberEmails(address=single_rpg)
                    member_tables.append(new_rpg)
                new_jct = ajdb.JCTMemberEmail(member=new_member,
                                              email=new_rpg,
                                              principal=principal)
                principal = False
                member_tables.append(new_jct)

        if val.get('telephone'):
            single_rpg = f"(+33){val['telephone']:9d}"
            matched_rpg = [elt for elt in member_tables
                            if isinstance(elt, ajdb.MemberPhones) and elt.number == single_rpg]
            if matched_rpg:
                new_rpg = matched_rpg[0]
            else:
                new_rpg = ajdb.MemberPhones(number=single_rpg)
                member_tables.append(new_rpg)
            new_jct = ajdb.JCTMemberPhone(member=new_member,
                                          phone=new_rpg,
                                          principal=True)
            member_tables.append(new_jct)

        if val.get('adresse'):
            matched_rpg = False
            matched_rpg = [elt for elt in member_tables
                            if     isinstance(elt, ajdb.MemberAddresses)
                            and elt.street_num == val['adresse'].get('numero')
                            and elt.street_name == val['adresse'].get('nom_voie')
                            and (not elt.street_type
                                 or elt.street_type.name == val['adresse'].get('type_voie')
                                )
                            and elt.zip_code == val['adresse'].get('cp')
                            and elt.city == val['adresse'].get('ville')
                            ]
            if matched_rpg:
                new_rpg = matched_rpg[0]
            else:
                new_rpg = ajdb.MemberAddresses()
                new_rpg.city=val['adresse']['ville']
                if val['adresse'].get('numero'):
                    new_rpg.street_num = val['adresse']['numero']
                if val['adresse'].get('type_voie'):
                    matched_type_voie = [elt for elt in lut_tables
                                    if isinstance(elt, ajdb.LUTStreetTypes) and elt.name == val['adresse']['type_voie']]
                    new_rpg.street_type = matched_type_voie[0]
                if val['adresse'].get('autre'):
                    new_rpg.extra = val['adresse']['autre']
                if val['adresse'].get('nom_voie'):
                    new_rpg.street_name = val['adresse']['nom_voie']
                if val['adresse'].get('cp'):
                    new_rpg.zip_code = val['adresse']['cp']
                member_tables.append(new_rpg)

            new_jct = ajdb.JCTMemberAddress(member=new_member,
                                            address=new_rpg,
                                            principal=True)
            member_tables.append(new_jct)

    async with aj_db.AsyncSessionMaker() as session:
        async with session.begin():
            session.add_all(member_tables)

    return member_tables

async def _populate_events_tables(aj_db:AjDb, lut_tables, member_tables):
    """ Populate all event related tables
    """
    try:
        xsldb_events = load_json_file(Path('aj_xls2db/xlsdb_suivi.json'))
    except FileNotFoundError:
        return

    membership_tables = []
    event_tables = []

    for val in xsldb_events['suivi']:
        # Membership
        if val['entree']['categorie'] == 'Cotisation':
            new_membership = ajdb.Memberships()
            membership_tables.append(new_membership)
            new_membership.date = datetime.fromisoformat(val['date']).date()
            new_membership.season       = [elt for elt in lut_tables    if isinstance(elt, ajdb.Seasons        ) and elt.name == val['entree']['nom']][0]
            new_membership.member       = [elt for elt in member_tables if isinstance(elt, ajdb.Members        ) and elt.id   == val['membre']['id']][0]
            new_membership.contribution = [elt for elt in lut_tables    if isinstance(elt, ajdb.LUTContribution) and elt.name == val['cotisation']][0]
            if val['membre'].get('prive'):
                new_membership.statutes_accepted   = val['membre']['prive'].get('approbation_statuts', '').lower() == 'oui'
                new_membership.has_civil_insurance = val['membre']['prive'].get('assurance_resp_civile', '').lower() == 'oui'
                new_membership.picture_authorized  = val['membre']['prive'].get('utilisation_image', '').lower() == 'oui'
            if val['membre'].get('source_connaissance'):
                new_membership.know_from = [elt for elt in lut_tables if isinstance(elt, ajdb.LUTKnowFrom) and elt.name == val['membre']['source_connaissance']][0]

        # Events
        if val['entree']['categorie'] == 'Evènement' and not val['entree'].get('detail'):
            new_event = ajdb.Events()
            event_tables.append(new_event)
            new_event.date   = datetime.fromisoformat(val['date']).date()
            new_event.season = [elt for elt in lut_tables if isinstance(elt, ajdb.Seasons) and new_event.date >= elt.start
                                                                                           and new_event.date <= elt.end][0]
            new_event.name   = val['entree']['nom']

        # Event - Member
        if (   (    val['entree']['categorie'] == 'Evènement'
                and val['entree'].get('detail') == 'Vote par pouvoir')
            or (val['entree']['categorie'] == 'Présence')):

            new_event = ajdb.JCTEventMember()
            event_tables.append(new_event)
            new_event.presence = val['entree']['categorie'] == 'Présence'
            matched_event = [elt for elt in event_tables if isinstance(elt, ajdb.Events) and elt.date == datetime.fromisoformat(val['date']).date()]
            if matched_event:
                new_event.event = matched_event[0]
            else:
                new_event.event = ajdb.Events()
                event_tables.append(new_event.event)
                new_event.event.date = datetime.fromisoformat(val['date']).date()
                new_event.event.season = [elt for elt in lut_tables if isinstance(elt, ajdb.Seasons) and new_event.event.date >= elt.start
                                                                                                     and new_event.event.date <= elt.end][0]
            if val.get('membre'):
                new_event.member = [elt for elt in member_tables if isinstance(elt, ajdb.Members) and elt.id == val['membre']['id']][0]

            if val.get('commentaire_old'):
                new_event.comment = val['commentaire_old']

        # Member - Asso role
        if val['entree']['categorie'] == 'Info Membre' and val.get('membre') and val['membre'].get('asso_role'):
            timestamp = datetime.fromisoformat(val['date']).date()
            member_id = val['membre']['id']
            matched_role = [elt for elt in lut_tables if isinstance(elt, ajdb.AssoRoles) and elt.name == val['membre']['asso_role']]
            if len([elt for elt in event_tables if isinstance(elt, ajdb.JCTMemberAssoRole)
                                                   and elt.member_id == member_id
                                                   and elt.asso_role == matched_role[0]]) == 0:
                new_event = ajdb.JCTMemberAssoRole(member_id = member_id,
                                                   asso_role = matched_role[0],
                                                   start = timestamp)
                event_tables.append(new_event)

    async with aj_db.AsyncSessionMaker() as session:
        async with session.begin():
            session.add_all(membership_tables)
            session.add_all(event_tables)





async def _main():
    """ main function
    """
    async with AjDb() as aj_db:

        # create all tables
        # -----------------
        await _create_db_schema(aj_db=aj_db)

        # Populate all tables
        # -------------------

        # lookup tables
        lut_tables = await _populate_lut_tables(aj_db=aj_db)
        if lut_tables:
            # member tables
            member_tables = await _populate_member_tables(aj_db=aj_db, lut_tables=lut_tables)
            if member_tables:
                # membership tables
                await _populate_events_tables(aj_db=aj_db, lut_tables=lut_tables, member_tables=member_tables)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
