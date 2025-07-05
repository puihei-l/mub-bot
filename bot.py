import os, discord, asyncio, sqlite3
from discord.ext import commands

class BotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(title="Help - Commands", color=discord.Color.blue())
        for command in self.bot.commands:
            embed.add_field(name=f"!{command.name}", value=command.help or "No description", inline=False)
        await ctx.send(embed=embed)

    @commands.command(help="Swap Shifts")
    async def swap(self, ctx):
        await ctx.send(f'Which shift would you like to swap?')