#to be run on a docker container
import interactions
from interactions import slash_command, slash_option, OptionType, SlashContext, Client, Intents, BrandColors
import subprocess
from bot_token import token
import re
import textwrap
servers = [
    1120883193063677972,
    1403077958943506612,
]

pico_ip = '192.168.1.51'
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
    if show_name:
        username = ctx.author.display_name
    else:
        username = 'anonymous'

    message = message.strip()
    message = " ".join(message.split())
    regex = r'[^ -~]| {2,}|_'
    matches_regex = re.findall(regex, message)
    if matches_regex != []:
        for i,v in enumerate(matches_regex):
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
        message = message.replace(' ', '+')
        subprocess.run([f"curl", f"http://{pico_ip}/?motd={message}&author={username}"], check=True)
    except subprocess.CalledProcessError as e:
        embed = interactions.Embed(
            title="Error sending the message",
            description=f'The alarm clock may be on low battery or shut off. Try again later!',
            color=BrandColors.RED
        )
        with open('log.log', 'a') as f:
            f.write(f'{e}\n')
    
        await ctx.send(embed=embed)
    except:
        embed = interactions.Embed(
            title="Other unexpected bug",
            description=f'twin idek what happened ikiab',
            color=BrandColors.RED
        )
        with open('log.log', 'a') as f:
            f.write(f'{e}\n')

        await ctx.send(embed=embed)
    else:
        embed = interactions.Embed(
        title="Message sent!",
        description="Sent message successfully!",
        color=BrandColors.GREEN
        )
        await ctx.send(embed=embed)
    
    return

bot.start(token)