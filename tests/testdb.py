""" test deployment of a DB instance
"""
import sys
import asyncio
from typing import cast
# from datetime import date
import tempfile
from pathlib import Path

import sqlalchemy as sa

from ajbot._internal.ajdb import AjDb, tables as db_t
from ajbot._internal.config import AjConfig, FormatTypes

def _test_format_types(objects):
    print('\n'.join(f"{o:{FormatTypes.RESTRICTED}} ****** {o:{FormatTypes.FULLSIMPLE}} ****** {o:{FormatTypes.FULLCOMPLETE}}" for o in objects))



async def _search_member(aj_db:AjDb, lookup_val):
    query_result = await aj_db.query_members(lookup_val)
    print('')
    print('')
    print('-------------------')
    for qr in query_result:
        print(f"{qr:{FormatTypes.RESTRICTED}}")
    print('-------------------')
    for qr in query_result:
        print(f"{qr:{FormatTypes.FULLSIMPLE}}")
    print('-------------------')
    for qr in query_result:
        print(f"{qr:{FormatTypes.FULLCOMPLETE}}")
        print('')
    print('-------------------')
    print('')
    print('')

async def _season_events(aj_db_session):
    query = sa.select(db_t.Event).where(db_t.Event.is_in_current_season)
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
    query = sa.select(db_t.MemberAddress).where(db_t.Member.address_principal is not None)
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
                # .with_only_columns(db_t.Member.id, db_t.Member.credential, sa.func.count(db_t.Member.memberships))\
    query = sa.select(db_t.Member)\
                .join(db_t.Member.event_member_associations)\
                .join(db_t.MemberEvent.event)\
                .join(db_t.Event.season)\
                .where(db_t.Season.name == season_name)\
                .group_by(db_t.Member)
    async with aj_db_session.AsyncSessionMaker() as session:
        async with session.begin():
            query_result = await session.execute(query)
    matched_items = query_result.scalars().all()
    matched_items.sort(key=lambda x: cast(db_t.Member, x).credential, reverse=False)
    for m in matched_items:
        presence = len([event for event in cast(db_t.Member, m).events
                        if event.season.name == season_name])
        print(f"{m:{FormatTypes.FULLSIMPLE}} - {presence} présence(s)")
    print(len(matched_items), 'item(s)')


# async def _test_create_query(aj_db:AjDb):
#     event_date = date(2026, 1, 15)
#     event_partipant_ids = [2, 3, 36, 155]

#     seasons = await aj_db.query_seasons(refresh_cache=True)

#     new_event = db_t.Event(date = event_date)
#     [new_event.season] = [s for s in seasons if new_event.date >= s.start and new_event.date <= s.end]

#     aj_db._aio_session.add(new_event)

#     await aj_db._aio_session.commit()
#     await aj_db._aio_session.refresh(new_event)

#     aj_db._aio_session.add_all([db_t.MemberEvent(member_id = i, event_id=new_event.id, presence = True) for i in event_partipant_ids])

#     new_event.name = 'Coucou'


# async def _test_update_query(aj_db:AjDb):
#     query = sa.select(db_t.Event).where(db_t.Event.id == 102)
#     query_result = await aj_db._aio_session.execute(query)
#     my_event = query_result.scalars().one_or_none()

#     print(my_event)
#     print('\r\n'.join([str(m) for m in my_event.members]))

#     my_event.name += ' ...'
#     await aj_db._aio_session.delete(my_event.members[0])  # remove first member from event
#     await aj_db._aio_session.commit()
#     await aj_db._aio_session.refresh(my_event)

#     print("----------------------------------")
#     print(my_event)
#     print('\r\n'.join([str(m) for m in my_event.members]))


async def _test_stuff():
    async with AjDb() as aj_db:
        await _search_member(aj_db, 'vincent')
        await _season_events(aj_db)
        await _principal_address(aj_db)

        await _test_query(aj_db)
        # await _test_create_query(aj_db)
        # await _test_update_query(aj_db)




##################################################################

async def _test_membership_format():
    with AjConfig() as aj_config:
        async with AjDb(aj_config=aj_config) as aj_db:
            items = await aj_db.query_table_content(db_t.Membership)
            _test_format_types(items)


async def _test_query_members_per_season_presence():
    async with AjDb() as aj_db:
        season_name = '2025-2026'
        format_style = FormatTypes.FULLSIMPLE

        participants = await aj_db.query_members_per_season_presence(season_name)
        subscribers = await aj_db.query_members_per_season_presence(season_name, subscriber_only=True)
        if participants:
            summary = f"{len(participants)} personne(s) sont venues"

            reply = ''
            if len(subscribers) > 0:
                reply += f"## {len(subscribers)} Cotisant(es):\n- "
                reply += '\n- '.join(f"{m:{format_style}} - **{m.season_presence_count(season_name)}** participation(s)" for m in subscribers)
            if len(participants) - len(subscribers) > 0:
                sep = '\n\n'
                reply += f"{sep if len(subscribers) else ''}## {len(participants) - len(subscribers)} non Cotisant(es):\n- "
                reply += '\n- '.join(f"{m:{format_style}} - **{m.season_presence_count(season_name)}** participation(s)" for m in participants if m not in subscribers)
        else:
            if subscribers:
                summary = f"Je ne sais pas combien de personne sont venues, mais {len(subscribers)} ont cotisé :"
                reply = '- ' + '\n- '.join(f"{m:{format_style}}" for m in subscribers)
            else:
                summary = "😱 Mais il n'y a eu personne ! 😱"
                reply = '---'

    print(summary)
    print(reply)

async def _test_query_members_per_event_presence():
    async with AjDb() as aj_db:
        event_id = 97
        format_style = FormatTypes.FULLSIMPLE

        participants = await aj_db.query_members_per_event_presence(event_id)
        summary = f"{len(participants)} personne(s) sont venues"
        reply = '- '
        if participants:
            participants.sort(key=lambda x:x.credential)
            reply += '\n- '.join(f"{m:{format_style}}" for m in participants)

    print(summary)
    print(reply)

async def _test_generate_sign_sheet():
    # Create a sign sheet PDF file for all members with presence in current season
    # Store it in a spooled file (max 1MB in memory, then on disk)
    with AjConfig() as aj_config:
        async with AjDb(aj_config=aj_config) as aj_db:
            with tempfile.SpooledTemporaryFile(max_size=1024*1024, mode='w+b') as temp_file:

                await aj_db.query_member_sign_sheet(temp_file)

                temp_file.fileno()
                input(f"PDF created: {Path(temp_file.name)}, press Enter to continue...")




async def _test_member():
    await _test_membership_format()
    await _test_query_members_per_season_presence()
    await _test_query_members_per_event_presence()

    await _test_generate_sign_sheet()    #must be last as it wait for user input





##################################################################

async def _test_query_events():
    print("*"*20)
    for event in [None, "Jan 10 2025 - Epiphanie 2025"]:
        print(f"Testing query_events with {event if event else "--"}")
        print("--- Lazy loading")
        async with AjDb() as aj_db:
            events_lazy = await aj_db.query_events(event, lazyload=True)
            try:
                _test_format_types(events_lazy)
            except sa.exc.StatementError:
                print("Cannot print - excepted since we're lazy loading data")
        print("--- Eager loading")
        async with AjDb() as aj_db:
            events_eager = await aj_db.query_events(event, lazyload=False)
            _test_format_types(events_eager)
        print("\r\n" * 3)

async def _test_query_events_per_season():
    print("*"*20)
    for season in [None, "2023-2024"]:
        print(f"Testing query_events_per_season with {season if season else "--"}")
        print("--- Lazy loading")
        async with AjDb() as aj_db:
            events_lazy = await aj_db.query_events_per_season(season, lazyload=True)
            try:
                _test_format_types(events_lazy)
            except sa.exc.StatementError:
                print("Cannot print - excepted since we're lazy loading data")
        print("--- Eager loading")
        async with AjDb() as aj_db:
            events_eager = await aj_db.query_events_per_season(season, lazyload=False)
            _test_format_types(events_eager)
        print("\r\n" * 3)

async def _test_add_update_event():
    async with AjDb(modifier_discord="vbrett") as aj_db:
        event = await aj_db.add_update_event(event_id=101,
                                            #  event_date=date(2026, 1, 18),
                                             event_name="bubou",
                                             participant_ids=[36,151,14],)
    _test_format_types([event])


async def _test_event():
    await _test_query_events_per_season()
    await _test_query_events()
    await _test_add_update_event()






##################################################################
##################################################################
##################################################################
async def _main():
    """ main function - async version
    """

    # Original test
    # await _test_stuff()

    # Test event stuff
    await _test_event()

    # Test member stuff
    await _test_member()    #must be last as it wait for user input


    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
