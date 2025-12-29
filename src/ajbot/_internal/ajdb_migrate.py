""" Migrate excel file to db
"""
import sys
import asyncio
from datetime import datetime
from typing import cast
from pathlib import Path

from vbrpytools.exceltojson import ExcelWorkbook

from ajbot._internal.config import set_migrate_mode
set_migrate_mode()
from ajbot._internal.ajdb import AjDb , tables as db_t   #pylint: disable=wrong-import-position #set migrate mode called explicitelly before import ajdb & db_t


async def _create_db_schema(aj_db:AjDb):
    """ Drop and recreate db schema
    """
    await aj_db.drop_create_schema()


async def _populate_lut_tables(aj_db:AjDb, ajdb_xls:ExcelWorkbook):
    """ Populate lookup tables
    """

    lut_tables = []
    for val in ajdb_xls.dict_from_table('saisons'):
        lut_tables.append(db_t.Season(name=val['nom'],
                                      start=cast(datetime, val['debut']).date(),
                                      end=cast(datetime, val['fin']).date()))
    for val in ajdb_xls.dict_from_table('contribution'):
        lut_tables.append(db_t.ContributionType(name=val['val']))
    for val in ajdb_xls.dict_from_table('connaissance'):
        lut_tables.append(db_t.KnowFromSource(name=val['val']))
    for val in ajdb_xls.dict_from_table('compte'):
        lut_tables.append(db_t.AccountType(name=val['val']))
    for val in ajdb_xls.dict_from_table('type_voie'):
        lut_tables.append(db_t.StreetType(name=val['val']))

    for val in ajdb_xls.dict_from_table('discord_role'):
        new_discord_role = db_t.DiscordRole(name=val['val'],
                                             id=int(val['id']),)
        lut_tables.append(new_discord_role)
    for val in ajdb_xls.dict_from_table('roles'):
        new_asso_role = db_t.AssoRole(name=val['asso'])
        lut_tables.append(new_asso_role)
        if val.get('discord'):
            for d_role in val['discord'].split(','):
                [matched_discord_role] = [elt for elt in lut_tables
                                if isinstance(elt, db_t.DiscordRole) and elt.name == d_role]
                new_asso_role.discord_roles.append(matched_discord_role)

        if val.get('is_member') is not None:
            new_asso_role.is_member=bool(val.get('is_member'))
        if val.get('is_past_subscriber') is not None:
            new_asso_role.is_past_subscriber=bool(val.get('is_past_subscriber'))
        if val.get('is_subscriber') is not None:
            new_asso_role.is_subscriber=bool(val.get('is_subscriber'))
        if val.get('is_manager') is not None:
            new_asso_role.is_manager=bool(val.get('is_manager'))
        if val.get('is_owner') is not None:
            new_asso_role.is_owner=bool(val.get('is_owner'))

    async with aj_db.AsyncSessionMaker() as session:
        async with session.begin():
            session.add_all(lut_tables)

    return lut_tables


async def _populate_member_tables(aj_db:AjDb, ajdb_xls:ExcelWorkbook, lut_tables):
    """ Populate member tables
    """
    member_tables = []
    for val in ajdb_xls.dict_from_table('annuaire'):
        if not isinstance(val['creation']['date'], datetime):
            continue
        new_member = db_t.Member()
        member_tables.append(new_member)

        new_member.id=int(val['id'])

        if val.get('pseudo_discord'):
            new_member.discord_pseudo=db_t.DiscordPseudo(name=val['pseudo_discord'])

        if val.get('prenom') or val.get('nom') or val.get('date_naissance'):
            new_member.credential = db_t.Credential()
            new_member.credential.first_name=val.get('prenom')
            new_member.credential.last_name=val.get('nom')
            if val.get('date_naissance'):
                new_member.credential.birthdate = cast(datetime, val['date_naissance']).date()

        if val.get('emails'):
            principal = True
            for single_rpg in val['emails'].split(';'):
                matched_rpg = [elt for elt in member_tables
                            if isinstance(elt, db_t.Email) and elt.address == single_rpg]
                if matched_rpg:
                    new_rpg = matched_rpg[0]
                else:
                    new_rpg = db_t.Email(address=single_rpg)
                    member_tables.append(new_rpg)
                new_jct = db_t.MemberEmail(member=new_member,
                                              email=new_rpg,
                                              principal=principal)
                principal = False
                member_tables.append(new_jct)

        if val.get('telephone'):
            single_rpg = f"(+33){val['telephone']:9d}"
            matched_rpg = [elt for elt in member_tables
                            if isinstance(elt, db_t.Phone) and elt.number == single_rpg]
            if matched_rpg:
                new_rpg = matched_rpg[0]
            else:
                new_rpg = db_t.Phone(number=single_rpg)
                member_tables.append(new_rpg)
            new_jct = db_t.MemberPhone(member=new_member,
                                          phone=new_rpg,
                                          principal=True)
            member_tables.append(new_jct)

        if val.get('adresse'):
            matched_rpg = False
            matched_rpg = [elt for elt in member_tables
                            if     isinstance(elt, db_t.PostalAddress)
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
                new_rpg = db_t.PostalAddress()
                new_rpg.city=val['adresse']['ville']
                if val['adresse'].get('numero'):
                    new_rpg.street_num = val['adresse']['numero']
                if val['adresse'].get('type_voie'):
                    matched_type_voie = [elt for elt in lut_tables
                                    if isinstance(elt, db_t.StreetType) and elt.name == val['adresse']['type_voie']]
                    new_rpg.street_type = matched_type_voie[0]
                if val['adresse'].get('autre'):
                    new_rpg.extra = val['adresse']['autre']
                if val['adresse'].get('nom_voie'):
                    new_rpg.street_name = val['adresse']['nom_voie']
                if val['adresse'].get('cp'):
                    new_rpg.zip_code = val['adresse']['cp']
                member_tables.append(new_rpg)

            new_jct = db_t.MemberAddress(member=new_member,
                                            address=new_rpg,
                                            principal=True)
            member_tables.append(new_jct)

    async with aj_db.AsyncSessionMaker() as session:
        async with session.begin():
            session.add_all(member_tables)

    return member_tables

async def _populate_events_tables(aj_db:AjDb, ajdb_xls:ExcelWorkbook, lut_tables, member_tables):
    """ Populate all event related tables
    """

    membership_tables = []
    event_tables = []

    for val in ajdb_xls.dict_from_table('suivi'):
        # Membership
        if val['entree']['categorie'] == 'Cotisation':
            new_membership = db_t.Membership()
            membership_tables.append(new_membership)
            new_membership.date = cast(datetime, val['date']).date()
            new_membership.season            = [elt for elt in lut_tables    if isinstance(elt, db_t.Season         ) and elt.name == val['entree']['nom']][0]
            new_membership.member            = [elt for elt in member_tables if isinstance(elt, db_t.Member         ) and elt.id   == val['membre']['id']][0]
            new_membership.contribution_type = [elt for elt in lut_tables    if isinstance(elt, db_t.ContributionType) and elt.name == val['cotisation']][0]
            if val['membre'].get('prive'):
                new_membership.statutes_accepted   = val['membre']['prive'].get('approbation_statuts', '').lower() == 'oui'
                new_membership.has_civil_insurance = val['membre']['prive'].get('assurance_resp_civile', '').lower() == 'oui'
                new_membership.picture_authorized  = val['membre']['prive'].get('utilisation_image', '').lower() == 'oui'
            if val['membre'].get('source_connaissance'):
                new_membership.know_from_source = [elt for elt in lut_tables if isinstance(elt, db_t.KnowFromSource) and elt.name == val['membre']['source_connaissance']][0]

        # Event
        if val['entree']['categorie'] == 'Evènement' and not val['entree'].get('detail'):
            matched_event = [elt for elt in event_tables if isinstance(elt, db_t.Event) and elt.date == cast(datetime, val['date']).date()]
            if matched_event:
                matched_event[0].name = val['entree']['nom']
            else:
                new_event = db_t.Event()
                event_tables.append(new_event)
                new_event.date   = cast(datetime, val['date']).date()
                new_event.season = [elt for elt in lut_tables if isinstance(elt, db_t.Season) and new_event.date >= elt.start
                                                                                                and new_event.date <= elt.end][0]
                new_event.name   = val['entree']['nom']

        # Event - Member
        if (   (    val['entree']['categorie'] == 'Evènement'
                and val['entree'].get('detail') == 'Vote par pouvoir')
            or (val['entree']['categorie'] == 'Présence')):

            new_memberevent = db_t.MemberEvent()
            event_tables.append(new_memberevent)
            new_memberevent.presence = val['entree']['categorie'] == 'Présence'
            matched_event = [elt for elt in event_tables if isinstance(elt, db_t.Event) and elt.date == cast(datetime, val['date']).date()]
            if matched_event:
                new_memberevent.event = matched_event[0]
            else:
                new_event = db_t.Event()
                event_tables.append(new_event)
                new_event.date = cast(datetime, val['date']).date()
                new_event.season = [elt for elt in lut_tables if isinstance(elt, db_t.Season) and new_event.date >= elt.start
                                                                                                and new_event.date <= elt.end][0]
                new_memberevent.event = new_event

            if val.get('membre'):
                new_memberevent.member = [elt for elt in member_tables if isinstance(elt, db_t.Member) and elt.id == val['membre']['id']][0]

            if val.get('commentaire_old'):
                new_memberevent.comment = val['commentaire_old']

        # Member - Asso role
        if val['entree']['categorie'] == 'Info Membre' and val.get('membre') and val['membre'].get('asso_role'):

            start = cast(datetime, val['date']).date()
            end = None
            if val['entree'].get('detail'):
                end = cast(datetime, val['entree']['detail']).date()
            member_id = val['membre']['id']
            [matched_role] = [elt for elt in lut_tables if isinstance(elt, db_t.AssoRole) and elt.name == val['membre']['asso_role']]
            previous_member_asso_roles = [elt for elt in event_tables if isinstance(elt, db_t.MemberAssoRole) and elt.member_id == member_id and not elt.end]

            assert len(previous_member_asso_roles) <= 1, f"Erreur dans la DB: Plusieurs rôles asso actifs pour le membre {member_id} !:\n{', '.join(m.member.name for m in previous_member_asso_roles)}"
            if len([elt for elt in previous_member_asso_roles if elt.asso_role == matched_role]) == 0:
                new_memberassorole = db_t.MemberAssoRole(member_id = member_id,
                                                  asso_role = matched_role,
                                                  start = start,
                                                  end = end)
                event_tables.append(new_memberassorole)

    async with aj_db.AsyncSessionMaker() as session:
        async with session.begin():
            session.add_all(membership_tables)
            session.add_all(event_tables)





async def _main():
    """ main function
    """
    async with AjDb() as aj_db:
        ajdb_xls_file = Path(sys.argv[1])
        try:
            ajdb_xls = ExcelWorkbook(ajdb_xls_file)
        except FileNotFoundError:
            print(f"Excel file '{ajdb_xls_file}' not found.")
            return 1

        # create all tables
        # -----------------
        await _create_db_schema(aj_db=aj_db)

        # Populate all tables
        # -------------------

        # lookup tables
        lut_tables = await _populate_lut_tables(aj_db=aj_db, ajdb_xls=ajdb_xls)
        if lut_tables:
            # member tables
            member_tables = await _populate_member_tables(aj_db=aj_db, ajdb_xls=ajdb_xls, lut_tables=lut_tables)
            if member_tables:
                # membership tables
                await _populate_events_tables(aj_db=aj_db, ajdb_xls=ajdb_xls, lut_tables=lut_tables, member_tables=member_tables)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
