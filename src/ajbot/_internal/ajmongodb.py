""" test deployment of a MongoDB instance
"""
import sys
# from pathlib import Path
import asyncio
from uuid import UUID, uuid4

from pymongo import AsyncMongoClient
# from pymongo.asynchronous import database as mongodb
from pydantic import BaseModel, Field

from ajbot._internal.config import AjConfig


class EventItem(BaseModel):
    """ class handling events
    """
    id: UUID = Field(default_factory=uuid4, alias="_id")
    name: str

# class Movie(BaseModel):
#     name: str
#     year: int

class AjDb():
    """ get the ajbot database
    """
    _aj_config: AjConfig
    _client: AsyncMongoClient
    _event_db : any
    _events : any

    def __init__(self, aj_config:AjConfig):
        self._aj_config = aj_config
        # self._movies = mongodb. Database[Movie] = self._client.movie

    async def __aenter__(self):
        self._client = AsyncMongoClient(self._aj_config._config_dict.get("mongodb_uri"),
                                        uuidRepresentation="standard")
        self._event_db = self._client.eventlist
        self._events = self._event_db.events

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self._client.close()

    async def create_event(self, name):
        """ event to create a event entry
        """
        new_event = EventItem(name=name)
        await self._events.insert_one(new_event.model_dump(by_alias=True))
        return new_event

    # async def create_movie(self, name, year):
    #     """ event to create a movie entry
    #     """
    #     new_movie = Movie(name=name, year=year)
    #     await self._movies.insert_one(new_movie.model_dump(by_alias=True))
    #     return new_movie




async def _main():
    """ main function
    """
    with AjConfig(break_if_missing=True,
                  save_on_exit=False,                                 #TODO: change to True
                 ) as aj_config:

        name = "test event"
        aj_db = AjDb(aj_config)
        new_event = await aj_db.create_event(name)
        print(f"Created event: {new_event}")
        # new_movie = await aj_db.create_movie("test movie", 2020)
        # print(f"Created movie: {new_movie}")

        await aj_db._client.close()

    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
