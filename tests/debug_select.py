import sqlalchemy as sa
from ajbot._internal import ajdb_tables as ajdb_t

def try_stmt(desc, builder):
    print(f"\n{desc}")
    try:
        stmt = builder()
        print('stmt object:', stmt)
        try:
            print('Compiled SQL:')
            print(stmt.compile(compile_kwargs={"literal_binds": True}))
        except Exception as e:
            print('Compile failed:', type(e).__name__, e)
    except Exception as e:
        print('Construction failed:', type(e).__name__, e)

try_stmt('sa.select(Event).join(Season)', lambda: sa.select(ajdb_t.Event).join(ajdb_t.Season))
try_stmt('sa.select(Event).join(Event.season)', lambda: sa.select(ajdb_t.Event).join(ajdb_t.Event.season))

try_stmt('sa.select(Member)', lambda: sa.select(ajdb_t.Member))
try_stmt('sa.select(Event).where(Event.season.has(Season.name=="X"))', lambda: sa.select(ajdb_t.Event).where(ajdb_t.Event.season.has(ajdb_t.Season.name == 'X')))

print('\nInspecting mappers and relationships')
try:
    insp = sa.inspect(ajdb_t.Event)
    print('Event mapper found. relationships:')
    for r in insp.relationships:
        print(' -', r.key, '->', getattr(r, 'entity', r))
except Exception as e:
    print('Event inspect failed:', type(e).__name__, e)

try:
    insp_s = sa.inspect(ajdb_t.Season)
    print('Season mapper found. relationships:')
    for r in insp_s.relationships:
        print(' -', r.key, '->', getattr(r, 'entity', r))
except Exception as e:
    print('Season inspect failed:', type(e).__name__, e)

print('\nEvent column attributes:')
try:
    for c in insp.column_attrs:
        print(' -', c.key, type(c))
except Exception as e:
    print('Event column attrs failed:', type(e).__name__, e)

print('\nEvent table columns:')
try:
    print(list(getattr(ajdb_t.Event, '__table__').columns))
except Exception as e:
    print('Event __table__ access failed:', type(e).__name__, e)

print('\nTrying alternative join forms')
try_stmt('join_from(Event, Season)', lambda: sa.select(ajdb_t.Event).join_from(ajdb_t.Event, ajdb_t.Season))
try_stmt('where(Event.season_id == Season.id)', lambda: sa.select(ajdb_t.Event).where(ajdb_t.Event.season_id == ajdb_t.Season.id))
