""" This example requires the 'message_content' intent.
"""
import asyncio

import discord
import keyring
from pwinput import pwinput

async def main():
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

            @client.event
            async def on_ready():
                """ Called when the bot is ready. """
                print(f'We have logged in as {client.user}')

            @client.event
            async def on_message(message):
                """ Called when a message is sent. """
                if message.author == client.user:
                    return

                if message.content.startswith('$bye'):
                    await message.channel.send('Bye!')
                    await client.close()

                if message.content.startswith('$members'):
                    header = ['id', 'name', 'disp_name', 'joined_at', 'roles']
                    member_info = [[str(member.id),
                                    member.name,
                                    member.display_name,
                                    member.joined_at.isoformat(),
                                    ','.join([role.name for role in member.roles])]
                                for member in client.get_all_members()]
                    message_content = ";".join(header) + "\r\n" + '\r\n'.join([";".join(member) for member in member_info])

                    await message.channel.send(message_content)

            await client.start(token)
            continue_running = False

        except discord.errors.LoginFailure:
            await client.close()
            print("Invalid token. Please enter a valid token:")
            token = pwinput("", mask="*")
            keyring.set_password(keyring_server, keyring_user, token)
            continue_running = True

    print("Bot has shutdown.")

if __name__ == "__main__":
    asyncio.run(main())
