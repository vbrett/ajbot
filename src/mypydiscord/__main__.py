""" This example requires the 'message_content' intent.
"""
import sys
import asyncio

import discord
import keyring
from pwinput import pwinput
from vbrpytools.misctools import open_preserve

async def _async_main(output_file = None):
    """ main async function """
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    keyring_server = "discord"
    keyring_user = "mypydiscord"
    continue_running = True

    while continue_running:
        try:
            client = discord.Client(intents=intents)
            token = keyring.get_password(keyring_server, keyring_user)

            def member_info_csv(guilds=None):
                """ Returns a CSV string of members info in the guild.
                    guilds: list of guild names to include members from.
                            If None, all guilds the bot is in are used.
                """
                header = ['server', 'name', 'disp_name', 'joined_at', 'roles']
                member_info = [[member.guild.name,
                                member.name,
                                member.display_name,
                                member.joined_at.isoformat(),
                                ','.join([role.name for role in member.roles])]
                            for member in client.get_all_members() if (guilds is None or member.guild.name in guilds)]

                csv_content = ";".join(header) + "\n" + '\n'.join([";".join(member) for member in member_info])
                return csv_content

            @client.event
            async def on_ready():
                """ Called when the bot is ready. """
                print(f'We have logged in as {client.user}')
                if output_file:
                    with open_preserve(output_file, 'w') as f:
                        f.write(member_info_csv())

            @client.event
            async def on_message(message):
                """ Called when a message is sent. """
                if message.author == client.user:
                    return

                if message.content.startswith('$bye'):
                    await message.channel.send('Bye!')
                    await client.close()

                if message.content.startswith('$members'):
                    await message.reply(member_info_csv([message.guild.name]))

            await client.start(token)
            continue_running = False

        except (discord.errors.LoginFailure) as e:
            await client.close()
            if isinstance(e, discord.errors.LoginFailure):
                print("Invalid token. Please enter a valid token:")
                token = pwinput("", mask="*")
                keyring.set_password(keyring_server, keyring_user, token)
                continue_running = True

    print("Bot has shutdown.")

def _main():
    """ main function """
    asyncio.run(_async_main(sys.argv[1] if len(sys.argv) > 1 else None))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
