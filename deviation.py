import asyncio
import re

CLEANR = re.compile('<.*?>') 

import aiohttp
from bs4 import BeautifulSoup
from dotenv import dotenv_values
from sqlalchemy import delete, select  # type: ignore
from sqlalchemy.dialects.postgresql import insert  # type: ignore
from sqlalchemy.ext.asyncio import create_async_engine  # type: ignore

from modals.deviant import Deviants

config = dotenv_values(".env")
if config["DATABASE_STRING"]:
    engine = create_async_engine(config["DATABASE_STRING"])

#URL = "https://www.gameskinny.com/tips/all-deviant-locations-in-once-human/"
URL = "https://mmo-wiki.com/once-human/complete-deviant-guide-in-once-human/"

async def main():
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            body = await response.text()
    soup = BeautifulSoup(body, 'lxml')
    divs = soup.find_all("div", {"class": "wp-block-media-text is-stacked-on-mobile"})
    for div in divs:
        img_url = div.find("img")['src']
        deviant_info = re.sub(CLEANR, '', str(div.find("p")))
        name = deviant_info.split("Type: ")[0].split(": ")[1].strip()
        sub_type = deviant_info.split("Type: ")[1].split("Mood")[0]
        happiness = deviant_info.split("Mood Booster: ")[1].split("Description")[0]
        effect = deviant_info.split("Description: ")[1].split("How to Acquire")[0]
        locations = deviant_info.split("How to Acquire: ")[1].split("Map Location")[0]
        async with engine.begin() as conn:
            await conn.execute(insert(Deviants).values(name=name, effect=effect, locations=locations, sub_type=sub_type, img_url=img_url, happiness=happiness).on_conflict_do_update(constraint='deviants_unique_name', set_={'effect': effect, 'sub_type': sub_type, 'locations': locations, 'img_url': img_url, 'happiness': happiness}))
        await engine.dispose(close=True)


asyncio.run(main())