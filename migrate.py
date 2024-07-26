import asyncio

from dotenv import dotenv_values
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine
from modals.channels import ReportingChannel

config = dotenv_values(".env")

if config["DATABASE_STRING"]:
    engine = create_async_engine(config["DATABASE_STRING"])
if config["DATABASE"]:
    old_engine = create_async_engine(f"sqlite+aiosqlite:///{config['DATABASE']}")

async def migrate():
    all_rows = []
    async with old_engine.begin() as conn:
        all_rows = await conn.execute(select(ReportingChannel.guild_id,ReportingChannel.channel_id,ReportingChannel.role_id))
        all_rows = all_rows.all()
    await old_engine.dispose(close=True)
    for row in all_rows:   
        async with engine.begin() as conn:
            print(row)
            insert_stmt = insert(ReportingChannel).values(guild_id=row.guild_id,channel_id=row.channel_id,role_id=row.role_id)
            update = insert_stmt.on_conflict_do_update(constraint='channels_unique_guildid', set_={'role_id': row.role_id}, index_elements=['guild_id', 'channel_id'])
            await conn.execute(update)
    await engine.dispose(close=True)

asyncio.run(migrate())