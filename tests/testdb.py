""" test deployment of a DB instance
"""
import sys
import asyncio
from typing import cast
from datetime import date

import sqlalchemy as sa
# from sqlalchemy import orm

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
    with AjConfig(save_on_exit=True) as aj_config:
        async with AjDb(aj_config=aj_config) as aj_db:

            query = sa.select(ajdb_t.Membership)
            # items = (await aj_db.aio_session.scalars(query)).all()
            items = await aj_db.query_members_per_season_presence()
            for i in items:
                print(f"{i}", '!!!!!' if cast(ajdb_t.Member, i).is_subscriber else '')


# SELECT
# 	id m_id,
# 	CASE
# 		WHEN EXISTS (SELECT asso_role_id FROM JCT_member_asso_role WHERE (member_id = m_id AND start <= NOW() AND (end IS NULL OR end >= NOW())))
# 		THEN  (SELECT asso_role_id FROM JCT_member_asso_role WHERE (member_id = m_id AND start <= NOW() AND (end IS NULL OR end >= NOW())))

# 		WHEN EXISTS (SELECT 1 FROM JCT_member_asso_role mar
#                      WHERE mar.member_id = m_id AND mar.start <= NOW() AND (mar.end IS NULL OR mar.end >= NOW())
#             		)
# 		THEN (SELECT JCT_member_asso_role.asso_role_id FROM JCT_member_asso_role
#                      WHERE JCT_member_asso_role.member_id = m_id AND JCT_member_asso_role.start <= NOW() AND (JCT_member_asso_role.end IS NULL OR JCT_member_asso_role.end >= NOW())
#             		)

# 		WHEN EXISTS (
#             		SELECT 1 FROM memberships ms
#             		WHERE ms.member_id = m_id AND EXISTS(SELECT 1 FROM seasons WHERE ms.season_id = seasons.id
#                                                          							 AND seasons.start <= NOW()
#                                                          							 AND (seasons.end IS NULL OR seasons.end >= NOW()))
#             		)
#         THEN (SELECT id FROM asso_roles WHERE is_subscriber = TRUE)

# 		WHEN EXISTS (
#             		SELECT 1 FROM memberships ms
#             		WHERE ms.member_id = m_id AND EXISTS(SELECT 1 FROM seasons WHERE ms.season_id = seasons.id
#                                                          							 AND seasons.end <= NOW())
#             		)
#         THEN (SELECT id FROM asso_roles WHERE is_past_subscriber = TRUE)

#         ELSE (SELECT id FROM asso_roles WHERE is_member = TRUE AND is_subscriber = FALSE AND is_past_subscriber = FALSE AND is_manager = FALSE AND is_owner = FALSE)
# 	END AS "current_asso_role"

# FROM members
# WHERE 1


async def _main():
    """ main function - async version
    """
    # async with AjDb() as aj_db:
        # """
        # execute all within same ajdb session
        # """

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
