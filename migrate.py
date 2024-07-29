import asyncio

from dotenv import dotenv_values
from sqlalchemy import select  # type: ignore
from sqlalchemy.dialects.postgresql import insert  # type: ignore
from sqlalchemy.ext.asyncio import create_async_engine  # type: ignore

from modals.channels import ReportingChannel
from modals.guild_blacklist import GuildBlacklist

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
            cur_strikes = await conn.execute(select(GuildBlacklist.strikes).filter_by(guild_id=row.guild_id))
            cur_strikes = cur_strikes.scalar()
            if cur_strikes is not None:
                continue
            insert_stmt = insert(GuildBlacklist).values(guild_id=row.guild_id)
            update = insert_stmt.on_conflict_do_nothing(constraint='guild_blacklist_unique_guild_id')
            await conn.execute(update)
            insert_stmt = insert(ReportingChannel).values(guild_id=row.guild_id,channel_id=row.channel_id,role_id=row.role_id)
            update = insert_stmt.on_conflict_do_update(constraint='channels_unique_guildid', set_={'role_id': row.role_id})
            await conn.execute(update)
    await engine.dispose(close=True)

asyncio.run(migrate())
