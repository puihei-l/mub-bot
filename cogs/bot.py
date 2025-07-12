import os, discord, asyncio, aiosqlite
from discord.ext import commands
from dotenv import load_dotenv

SECRETARY = os.getenv('SECRETARY_ID')
ADMIN = os.getenv('ADMIN_ID')

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
            embed.description = """Use !help [command] for more info on a command.
                                    You do not need the brackets."""
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

        Not developed yet. DO NOT USE.
        """
        await ctx.send(f'Which shift would you like to swap?')

    @commands.command()
    async def assign(self, ctx, coach = None, day = None, week = None, classLevel = None):
        """
        Assign shift

        **Usage:**
            !assign `coach` `day` `class level`
        
        **Example:**
            !assign `lenin` `tuesday` `combat`
        """

        def check(msg):
            return msg.author.id == SECRETARY and msg.channel == ctx.channel


    @commands.command()
    async def dropto(self, ctx, drop = None, pick = None, day = None, week = None, classLevel = None):
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
            if pick is None:
                await ctx.send(f'Who are you dropping it to?')
                pick_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                pick = pick_msg.content.strip().upper()
            if day is None:
                await ctx.send(f'Which day? (mon, tue, etc.)')
                day_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                day = day_msg.content.strip().upper()
            if week is None:
                await ctx.send(f'Week number? (1, 2, etc.)')
                week_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                week = week_msg.content.strip().upper()
            if classLevel is None:
                await ctx.send(f'Which level? (beg1, combat, etc.)')
                cl_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                classLevel = cl_msg.content.strip().upper()
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !dropto to restart")

        drop = drop.upper()
        pick = pick.upper()
        day = day.upper()
        classLevel = classLevel.upper()
        
        embed = discord.Embed(
            title="Shift drop request",
            color=discord.Color.dark_grey()
        )
        embed.description = f"""
            **From:** {drop}
            **To (Cover):** {pick}
            **Day:** {day}, Week {week}
            **Class Level:** {classLevel}
            """
        embed.set_footer(text="Contact the Secretary if anything is incorrect.")

        try:
            await ctx.send(f'Type `confirm` to confirm your choice')
            msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
            if msg.content == "confirm":
                async with aiosqlite.connect('Coach.db') as db:

                    cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (pick,))
                    result = await cursor.fetchone()
                    if result is None:
                        await ctx.send(f"Coach {pick} is not found.")
                        return
                    
                    coach_b_id = result[0]

                    cursorA = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (drop,))
                    resultA = await cursorA.fetchone()
                    if resultA is None:
                        await ctx.send(f"Coach {drop} is not found.")
                        return
                    
                    coach_a_id = resultA[0]

                    await db.execute(f"""UPDATE Classes
                                     SET coach_id = ?
                                     WHERE coach_id = ?
                                     AND day = ?
                                     AND week = ?
                                     AND class_level = ?;""",
                                     (coach_b_id, coach_a_id, day, week, classLevel,))
        
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !dropto to restart")
            return

async def setup(bot):
    await bot.add_cog(BotCog(bot))