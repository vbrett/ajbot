""" test deployment of a DB instance
"""
import sys
import asyncio
from typing import cast
from datetime import date

import sqlalchemy as sa

from ajbot._internal.ajdb import AjDb
from ajbot._internal import ajdb_tables as ajdb_t
from ajbot._internal.config import AjConfig, FormatTypes

async def _search_member(aj_db:AjDb, lookup_val):
    query_result = await aj_db.query_members(lookup_val)
    print('')
    print('')
    print('-------------------')
    for qr in query_result:
        print(f'{qr:{FormatTypes.RESTRICTED}}')
    print('-------------------')
    for qr in query_result:
        print(f'{qr:{FormatTypes.FULLSIMPLE}}')
    print('-------------------')
    for qr in query_result:
        print(f'{qr:{FormatTypes.FULLCOMPLETE}}')
        print('')
    print('-------------------')
    print('')
    print('')

async def _season_events(aj_db_session):
    query = sa.select(ajdb_t.Event).where(ajdb_t.Event.is_in_current_season)
    async with aj_db_session.AsyncSessionMaker() as session:
        async with session.begin():
            query_result = await session.execute(query)
    print('')
    print('')
    print('-------------------')
    matched_events = query_result.scalars().all()
    for e in matched_events:
        print(e)
    print(len(matched_events), 'évènement(s)')
    print('-------------------')

async def _principal_address(aj_db_session):
    query = sa.select(ajdb_t.MemberAddress).where(ajdb_t.Member.address_principal is not None)
    async with aj_db_session.AsyncSessionMaker() as session:
        async with session.begin():
            query_result = await session.execute(query)
    print('')
    print('')
    print('-------------------')
    matched_members = query_result.scalars().all()
    for e in matched_members:
        print(e.address)
    print(len(matched_members), 'membre(s) avec adresse principale')
    print('-------------------')


async def _test_query(aj_db_session):
    season_name = "2025-2026"
                # .with_only_columns(ajdb_t.Member.id, ajdb_t.Member.credential, sa.func.count(ajdb_t.Member.memberships))\
    query = sa.select(ajdb_t.Member)\
                .join(ajdb_t.MemberEvent)\
                .join(ajdb_t.Event)\
                .join(ajdb_t.Season)\
                .where(ajdb_t.Season.name == season_name)\
                .group_by(ajdb_t.Member)
    async with aj_db_session.AsyncSessionMaker() as session:
        async with session.begin():
            query_result = await session.execute(query)
    matched_items = query_result.scalars().all()
    matched_items.sort(key=lambda x: cast(ajdb_t.Member, x).credential, reverse=False)
    for m in matched_items:
        presence = len([member_event for member_event in cast(ajdb_t.Member, m).events
                        if member_event.event.season.name == season_name])
        print(f'{m:{FormatTypes.FULLSIMPLE}} - {presence} présence(s)')
    print(len(matched_items), 'item(s)')


async def _test_create_query(aj_db:AjDb):
    event_date = date(2025, 11, 21)
    event_partipant_ids = [2, 3, 36, 155]

    seasons = await aj_db.query_seasons()

    new_event = ajdb_t.Event(date = event_date)
    [new_event.season] = [s for s in seasons if new_event.date >= s.start and new_event.date <= s.end]

    aj_db.aio_session.add(new_event)
    aj_db.aio_session.add_all([ajdb_t.MemberEvent(member_id = i, event=new_event, presence = True) for i in event_partipant_ids])

    new_event.name = 'Coucou'


async def _test_update_query(aj_db:AjDb):
    query = sa.select(ajdb_t.Event).where(ajdb_t.Event.id == 102)
    query_result = await aj_db.aio_session.execute(query)
    my_event = query_result.scalars().one_or_none()

    print(my_event)
    print('\r\n'.join([str(m) for m in my_event.members]))

    my_event.name += ' ...'
    await aj_db.aio_session.delete(my_event.members[0])  # remove first member from event
    await aj_db.aio_session.commit()
    await aj_db.aio_session.refresh(my_event)

    print("----------------------------------")
    print(my_event)
    print('\r\n'.join([str(m) for m in my_event.members]))


async def _test_misc():
    # discord_roles = {config._KEY_OWNERS: [],
    #                  config._KEY_MANAGERS: [],
    #                  config._KEY_MEMBERS: []}
    # asso_roles = {}
    # async with AjDb() as aj_db:
    #     mapped_roles = await aj_db.query_discord_asso_roles()
    #     for mr in mapped_roles:
    #         mr = cast(ajdb_t.AssoRoleDiscordRole, mr)
    #         if mr.asso_role.is_owner and mr.discord_role_id not in discord_roles[config._KEY_OWNERS]:
    #             discord_roles[config._KEY_OWNERS].append(mr.discord_role_id)
    #         if mr.asso_role.is_manager and mr.discord_role_id not in discord_roles[config._KEY_MANAGERS]:
    #             discord_roles[config._KEY_MANAGERS].append(mr.discord_role_id)
    #         if mr.asso_role.is_member and mr.discord_role_id not in discord_roles[config._KEY_MEMBERS]:
    #             discord_roles[config._KEY_MEMBERS].append(mr.discord_role_id)
    #         if mr.asso_role.is_subscriber:
    #             assert discord_roles.get(config._KEY_SUBSCRIBER, mr.discord_role_id) == mr.discord_role_id, "Multiple subscriber discord roles mapped!"
    #             assert asso_roles.get(config._KEY_SUBSCRIBER, mr.asso_role_id) == mr.asso_role_id, "Multiple subscriber asso roles mapped!"
    #             discord_roles[config._KEY_SUBSCRIBER] = mr.discord_role_id
    #             asso_roles[config._KEY_SUBSCRIBER] = mr.asso_role_id
    #         if mr.asso_role.is_past_subscriber:
    #             assert discord_roles.get(config._KEY_PAST_SUBSCRIBER, mr.discord_role_id) == mr.discord_role_id, "Multiple past subscriber discord roles mapped!"
    #             assert asso_roles.get(config._KEY_PAST_SUBSCRIBER, mr.asso_role_id) == mr.asso_role_id, "Multiple past subscriber asso roles mapped!"
    #             discord_roles[config._KEY_PAST_SUBSCRIBER] = mr.discord_role_id
    #             asso_roles[config._KEY_PAST_SUBSCRIBER] = mr.asso_role_id

    # print(asso_roles)
    # print(discord_roles)
    with AjConfig(save_on_exit=True) as aj_config:
        async with AjDb(aj_config=aj_config) as aj_db:
            await aj_config.udpate_roles(aj_db=aj_db)
    print('Discord Owners roles:', aj_config.discord_owners)
    print('Discord Managers roles:', aj_config.discord_managers)
    print('Discord Members roles:', aj_config.discord_members)
    print('Discord Subscriber role:', aj_config.discord_subscriber)
    print('Discord Past subscriber role:', aj_config.discord_past_subscriber)
    print('Asso Subscriber role:', aj_config.asso_subscriber)
    print('Asso Past subscriber role:', aj_config.asso_past_subscriber)

async def _main():
    """ main function - async version
    """
    async with AjDb() as aj_db:
        """
        execute all within same ajdb session
        """

        # await _search_member(aj_db, 'vincent')
        # await _season_events(aj_db)
        # await _principal_address(aj_db)

        # await _test_query(aj_db)
        # await _test_create_query(aj_db)
        # await _test_update_query(aj_db)

    await _test_misc()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
