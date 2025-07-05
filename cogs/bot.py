import os, discord, asyncio, sqlite3
from discord.ext import commands

class BotCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx, optcmd = None):
    
        if optcmd is None:
            embed = discord.Embed(
                title="Help - Commands",
                color=discord.Color.blue()
            )
            embed.description = """Use !help [command] for more info on a command."""
            for cmd in self.bot.commands:
                if not cmd.hidden and cmd.name != "help":
                    short = getattr(cmd, "short_help", cmd.short_doc or "No description")
                    embed.add_field(name=f'!{cmd.name}', value=short, inline=False)
            await ctx.send(embed=embed)
        else:
            cmd = self.bot.get_command(optcmd)
            if cmd is None:
                await ctx.send(f'Command {optcmd} not found.')
            else:
                desc = cmd.help or "No description"
                embed = discord.Embed(
                    title=f"**Help for !{cmd.name}:**",
                    color=discord.Color.dark_purple()
                )
                embed.description = desc
                await ctx.send(embed=embed)

        

    @commands.command()
    async def swap(self, ctx, classLevel = None):
        """
        Swap shift
        """
        await ctx.send(f'Which shift would you like to swap?')


    @commands.command()
    async def dropto(self, ctx, drop = None, pick = None, day = None, week = None, classLevel = None, ):
        """
        Drop shift with cover
        
        **Usage:**
            !dropto `from` `to` `day` `week` `class level`
        
        **Example:**
            !dropto `lenin` `gab` `tuesday` `4` `combat`
        
        Use this command if you have a cover. Otherwise, contact the Secretary.
        """

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            if drop is None:
                await ctx.send(f'What is your name?')
                drop_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                drop = drop_msg.content.strip().upper()
            else:
                drop = drop.upper()
            if pick is None:
                await ctx.send(f'Who are you dropping it to?')
                pick_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                pick = pick_msg.content.strip().upper()
            else:
                pick = pick.upper()
            if day is None:
                await ctx.send(f'Which day? (mon, tue, etc.)')
                day_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                day = day_msg.content.strip().upper()
            else:
                day = day.upper()
            if week is None:
                await ctx.send(f'Week number? (1, 2, etc.)')
                week_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                week = week_msg.content.strip().upper()
            else:
                week = week.upper()
            if classLevel is None:
                await ctx.send(f'Which level? (beg1, combat, etc.)')
                cl_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                classLevel = cl_msg.content.strip().upper()
            else:
                classLevel = classLevel.upper()
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !dropto to restart")
        
        embed = discord.Embed(
            title="Shift drop confirmation",
            color=discord.Color.dark_grey()
        )
        embed.description = f"""
            **From:** {drop}
            **To (Cover):** {pick}
            **Day:** {day}, Week {week}
            **Class Level:** {classLevel}
            """
        embed.set_footer(text="Contact the Secretary if anything is incorrect.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BotCog(bot))