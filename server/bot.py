import interactions
from interactions import slash_command, slash_option, OptionType, SlashContext, Client, Intents, BrandColors, check, is_owner
import subprocess
from creds import token
import re
import textwrap
import time
import json
servers = [
    1120883193063677972,
    1403077958943506612,
]

pico_ip = '192.168.1.51'
server_ip = '192.168.1.21'
bot = Client(intents=Intents.DEFAULT, send_command_tracebacks=True)


@slash_command(name='message', scopes=servers)
@slash_option(
    name='message',
    description='',
    opt_type=OptionType.STRING,
    required=True
)
@slash_option(
    name='show_name',
    description='whether or not your name is attached to the message',
    opt_type=OptionType.BOOLEAN,
    required=False
)
async def send_message(ctx: SlashContext, message: str, show_name=True):
    await ctx.defer()
    if show_name:
        username = ctx.author.display_name
    else:
        username = 'anonymous'

    message = message.strip()
    message = " ".join(message.split())
    regex = r'[^ -~]| {2,}|_'
    matches_regex = re.findall(regex, message)
    if matches_regex != []:
        for i, v in enumerate(matches_regex):
            if ' ' in v:
                matches_regex[i] = 'double/more spaces'

        print("invalid")
        print(matches_regex)

        fail_message = f"""
        This message contains illegal characters.
        The following are not allowed:
        Double (or more) spaces
        Emojis
        External Ascii characters
        Underscores

        Try again and stick to the keyboard!
        Illegal characters: {matches_regex}
        """

        embed = interactions.Embed(
            title="Invalid characters",
            description=textwrap.dedent(fail_message),
            color=BrandColors.YELLOW
        )
        await ctx.send(embed=embed)
        return

    if len(message) > 100:
        embed = interactions.Embed(
            title="Too long",
            description="Keep message under 100 characters.",
            color=BrandColors.YELLOW
        )
        await ctx.send(embed=embed)
        return

    try:
        print("doing smth")
        message_format = message.replace(' ', '+')
        subprocess.run(
            [f"curl", f"http://{pico_ip}/?motd={message_format}&author={username}"], check=True, timeout=3)
        print("done")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print("gurt")
        try:
            now = int(time.time())
            new_motd = {
                "motd": message,
                "id": -1,
                "author": username,
                "time": now,
                "new": True
            }
            with open('motds_cache.json', 'r') as f:
                data = json.load(f)
            data.append(new_motd)
            newdata = data
            with open('motds_cache.json', 'w') as f:
                json.dump(newdata, f)

            print("good")

        except Exception as e:
            print(e)
            print("Bad")
            embed = interactions.Embed(
                title="Error sending the message",
                description=f'The alarm clock may be on low battery or shut off, and the server is offline. Try again later!',
                color=BrandColors.RED
            )
            with open('log.log', 'a') as f:
                f.write(f'{e}\n')

            await ctx.send(embed=embed)

        else:
            print("yeah")
            embed = interactions.Embed(
                title="Message sent!",
                description="Sent message successfully! However, the alarm clock is offline, so it was sent to the server cache instead. The clock will get the message when it boots again.",
                color=BrandColors.GREEN
            )
            await ctx.send(embed=embed)
            print("good 2")
    else:
        embed = interactions.Embed(
            title="Message sent!",
            description="Sent message successfully!",
            color=BrandColors.GREEN
        )
        await ctx.send(embed=embed)


@slash_command(name='alarm_message',
               description="Set the message displayed when the alarm goes off.",
               scopes=servers)
@slash_option(name='message', description='', opt_type=OptionType.STRING, required=True)
@check(is_owner())
async def set_alarm_message(ctx: SlashContext, message):
    await ctx.defer()

    message = message.strip()
    message = " ".join(message.split())
    regex = r'[^ -~]| {2,}|_'
    matches_regex = re.findall(regex, message)
    if matches_regex != []:
        for i, v in enumerate(matches_regex):
            if ' ' in v:
                matches_regex[i] = 'double/more spaces'

        print("invalid")
        print(matches_regex)

        fail_message = f"""
        This message contains illegal characters.
        The following are not allowed:
        Double (or more) spaces
        Emojis
        External Ascii characters
        Underscores

        Try again and stick to the keyboard!
        Illegal characters: {matches_regex}
        """

        embed = interactions.Embed(
            title="Invalid characters",
            description=textwrap.dedent(fail_message),
            color=BrandColors.YELLOW
        )
        await ctx.send(embed=embed)
        return

    if len(message) > 100:
        embed = interactions.Embed(
            title="Too long",
            description="Keep message under 100 characters.",
            color=BrandColors.YELLOW
        )
        await ctx.send(embed=embed)
        return

    try:
        print("doing smth")
        message_format = message.replace(' ', '+')
        subprocess.run(
            [f"curl", f"http://{pico_ip}/?alarm_msg={message_format}"], check=True, timeout=3)
        print("done")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print("gurt")
        try:
            with open('alarm_message_cache.txt', 'w') as f:
                f.write(message)

        except Exception as e:
            print(e)
            print("Bad")
            embed = interactions.Embed(
                title="Error sending the alarm message",
                description=f'The alarm clock may be on low battery or shut off, and the server is offline. Try again later!',
                color=BrandColors.RED
            )
            with open('log.log', 'a') as f:
                f.write(f'{e}\n')

            await ctx.send(embed=embed)

        else:
            print("yeah")
            embed = interactions.Embed(
                title="Alarm message sent!",
                description="Sent alarm message successfully! However, the alarm clock is offline, so it was sent to the server cache instead. The clock will get the message when it boots again.",
                color=BrandColors.GREEN
            )
            await ctx.send(embed=embed)
            print("good 2")
    else:
        # TODO: let the user know that 'random' means selecting a random MOTD instead of actually displaying 'random'
        embed = interactions.Embed(
            title="Alarm message sent!",
            description="Sent alarm message successfully!",
            color=BrandColors.GREEN
        )
        await ctx.send(embed=embed)

bot.start(token)
