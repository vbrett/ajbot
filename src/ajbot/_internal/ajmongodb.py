""" test deployment of a MongoDB instance
"""
import sys
from pathlib import Path
import asyncio
from uuid import UUID, uuid4

from pymongo import AsyncMongoClient
from pydantic import BaseModel, Field

from ajbot._internal.config import AjConfig

aj_config = AjConfig(break_if_missing=True,
                     save_on_exit=False,                                 #TODO: change to True
                    )


client = AsyncMongoClient(aj_config._config_dict.get("mongodb_uri"),
                          uuidRepresentation="standard")
event_db = client.eventlist
events = event_db.events

class EventItem(BaseModel):
    """ class handling events
    """
    id: UUID = Field(default_factory=uuid4, alias="_id")
    name: str

async def create_event(name):
    """ event to create a event entry
    """
    new_event = EventItem(name=name)
    await events.insert_one(new_event.model_dump(by_alias=True))
    return new_event




def _main():
    """ main function
    """
    name = "test event"
    new_event = asyncio.run(create_event(name))
    print(f"Created event: {new_event}")
    return 0

if __name__ == "__main__":
    sys.exit(_main())
