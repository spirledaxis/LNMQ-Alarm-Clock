#to be run on the server, rather than the pico
import interactions
from interactions import slash_command, slash_option, OptionType, SlashContext, Client, Intents, BrandColors
import subprocess
from server.bot_token import token
import config
servers = [
    1120883193063677972
]
bot = Client(intents=Intents.DEFAULT, send_command_tracebacks=True)

@slash_command(name='message', scopes=servers)
@slash_option(
        name='message',
        description='',
        opt_type=OptionType.STRING,
        required=True
)
@slash_option(
    name='anonymity',
    description='whether or not your name is attached to the message',
    opt_type=OptionType.BOOLEAN,
    required=True
)
# @slash_option(
#     name='notify',
#     description='Alarm clock will display notification, so Neel will see it faster',
#     opt_type=OptionType.BOOLEAN,
# )

async def send_message(ctx: SlashContext, message: str, anonymity):
    if anonymity:
        username = ctx.author.display_name
    else:
        username = 'anonymous'
    
    message = message.replace(' ', '+') 
    try:
        subprocess.run([f"curl", f"http://{config.ip}/?motd={message}&author={username}"], check=True)
    except subprocess.CalledProcessError as e:
        embed = interactions.Embed(
            title="Error sending the message",
            description=f'The alarm clock may be on low battery or shut off. Try again later!',
            color=BrandColors.RED
        )
        print(e)
        await ctx.send(embed=embed)
    except:
        embed = interactions.Embed(
            title="Try again bud",
            description=f'theres a bug!',
            color=BrandColors.RED
        )
        print(e)
        await ctx.send(embed=embed)
    else:
        embed = interactions.Embed(
        title="Created Schedule",
        description="Sent message successfully!",
        color=BrandColors.GREEN
    )
    await ctx.send(embed=embed)


bot.start(token)