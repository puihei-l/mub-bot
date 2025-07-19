import os, discord, asyncio, aiosqlite
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
SECRETARY = int(os.getenv('SECRETARY_ID'))
ADMIN = int(os.getenv('ADMIN_ID'))
WEEKS = 12

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
            for cmd in sorted(self.bot.commands, key=lambda c: c.name):
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
    async def assignm(self, ctx, coach, day, classLevel):
        """
        Used by Admin/Secretary only (Bulk assign classes to a coach)

        **Usage:**
            !assignm `coach` `day` `class level`
        
        **Example:**
            !assignm `lenin` `2` `combat`
        
        """
        def check(msg):
            return msg.author.id == ADMIN and msg.channel == ctx.channel
        
        if not ctx.author.id == ADMIN:
            await ctx.send(f"You don't have permission to !assignm")
            return
        
        if (coach == None or day == None or classLevel == None):
            await ctx.send(f"Use !help assignm for usage")
            return

        coach = coach.upper()
        day = day.upper()
        classLevel = classLevel.upper()

        async with aiosqlite.connect('Coach.db') as db:
            cursor = await db.execute("""SELECT id FROM Classes
                                        WHERE day = ?
                                        AND UPPER(level) = ?;""", (day, classLevel,))
            result = await cursor.fetchall()
            if result is None:
                await ctx.send(f"No {classLevel} classes on day {day}")
                return

            cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach,))
            id = await cursor.fetchone()
            if id is None:
                await ctx.send(f"Coach {coach} is not found.")
                return
            
            coach_id = id[0]

            for row in result:
                class_id = row[0]
                await db.execute(f"""INSERT INTO CoachClasses (class_id, coach_id)
                                VALUES (?,?);""",
                                (class_id, coach_id,))
                await db.commit()


    @commands.command()
    async def drop(self, ctx, classLevel = None):
        """
        Drop shift

        Not developed yet. DO NOT USE.
        """

        def check(msg):
            return msg.author.id == ADMIN and msg.channel == ctx.channel
        
        try:
            if coach is None:
                await ctx.send(f'What is your name?')
                coach_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if coach_msg is None:
                    await ctx.send("No input. Request cancelled")
                    return
                coach = coach_msg.content.strip()
            if day is None:
                await ctx.send(f'Which day? (1 for monday, 2 for tuesday, etc.)')
                day_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if day_msg is None:
                    await ctx.send("No input. Request cancelled")
                    return
                day = day_msg.content.strip()
            if week is None:
                await ctx.send(f'Week number? (1, 2, etc.)')
                week_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if week_msg is None:
                    await ctx.send("No input. Request cancelled")
                    return
                week = week_msg.content.strip()
            if classLevel is None:
                await ctx.send(f'Which level? (beg1, combat, etc.)')
                cl_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if cl_msg is None:
                    await ctx.send("No input. Request cancelled")
                    return
                classLevel = cl_msg.content.strip()
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !assign to restart")
            return

        coach = coach.upper()
        classLevel = classLevel.upper()
        
        embed = discord.Embed(
            title="Shift drop request",
            color=discord.Color.dark_grey()
        )
        embed.description = f"""
            **From:** {coach}
            **Day:** {day}, Week {week}
            **Class Level:** {classLevel}
            """
        embed.set_footer(text="Contact the Secretary if anything is incorrect.")

        try:
            await ctx.send(f'Type `confirm` to confirm your choice')
            msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
            if msg.content == "confirm":
                async with aiosqlite.connect('Coach.db') as db:

                    cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach,))
                    result = await cursor.fetchone()
                    if result is None:
                        await ctx.send(f"Coach {coach} is not found.")
                        return
                    
                    coach_id = result[0]

                    cursor = await db.execute("""SELECT id FROM Classes
                                              WHERE day = ?
                                              AND week = ?
                                              AND level = ?;""", (day, week, classLevel,))
                    result = await cursor.fetchone()
                    if result is None:
                        await ctx.send(f"Class D{day} W{week} L{classLevel} is not found.")
                        return
                    
                    class_id = result[0]

                    await db.execute(f"""INSERT INTO CoachClasses (class_id, coach_id)
                                     VALUES (?,?);""",
                                     (class_id, coach_id))
                    await self.bot.db.commit()
            else:
                await ctx.send("Cancelling request")
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !dropto to restart")
            return

    @commands.command()
    async def assign(self, ctx, coach: str = None, day = None, week = None, classLevel = None):
        """
        Assign shift

        **Usage:**
            !assign `coach` `day` `week` `class level`
        
        **Example:**
            !assign `lenin` `2` `12` `combat`
        """

        if not ctx.author.id == SECRETARY:
            await ctx.send("Go away")
            return

        def check(msg):
            return msg.author.id == ADMIN and msg.channel == ctx.channel
        
        try:
            if coach is None:
                await ctx.send(f'What is your name?')
                coach_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if coach_msg is None:
                    await ctx.send("No input. Request cancelled")
                    return
                coach = coach_msg.content.strip()
            if day is None:
                await ctx.send(f'Which day? (1 for monday, 2 for tuesday, etc.)')
                day_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if day_msg is None:
                    await ctx.send("No input. Request cancelled")
                    return
                day = day_msg.content.strip()
            if week is None:
                await ctx.send(f'Week number? (1, 2, etc.)')
                week_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if week_msg is None:
                    await ctx.send("No input. Request cancelled")
                    return
                week = week_msg.content.strip()
            if classLevel is None:
                await ctx.send(f'Which level? (beg1, combat, etc.)')
                cl_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                if cl_msg is None:
                    await ctx.send("No input. Request cancelled")
                    return
                classLevel = cl_msg.content.strip()
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !assign to restart")
            return

        coach = coach.upper()
        classLevel = classLevel.upper()
        
        embed = discord.Embed(
            title="Shift drop request",
            color=discord.Color.dark_grey()
        )
        embed.description = f"""
            **From:** {coach}
            **Day:** {day}, Week {week}
            **Class Level:** {classLevel}
            """
        embed.set_footer(text="Contact the Secretary if anything is incorrect.")

        try:
            await ctx.send(f'Type `confirm` to confirm your choice')
            msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
            if msg.content == "confirm":
                async with aiosqlite.connect('Coach.db') as db:

                    cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (coach,))
                    result = await cursor.fetchone()
                    if result is None:
                        await ctx.send(f"Coach {coach} is not found.")
                        return
                    
                    coach_id = result[0]

                    cursor = await db.execute("""SELECT id FROM Classes
                                              WHERE day = ?
                                              AND week = ?
                                              AND level = ?;""", (day, week, classLevel,))
                    result = await cursor.fetchone()
                    if result is None:
                        await ctx.send(f"Class D{day} W{week} L{classLevel} is not found.")
                        return
                    
                    class_id = result[0]

                    await db.execute(f"""INSERT INTO CoachClasses (class_id, coach_id)
                                     VALUES (?,?);""",
                                     (class_id, coach_id))
                    await self.bot.db.commit()
            else:
                await ctx.send("Cancelling request")
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !dropto to restart")
            return



    @commands.command()
    async def dropto(self, ctx, drop = None, pick = None, day = None, week = None, classLevel = None):
        """
        Drop shift with cover
        
        **Usage:**
            !dropto `from` `to` `day` `week` `class level`
        
        **Example:**
            !dropto `lenin` `gab` `2` `12` `combat`
        
        Use this command if you have a cover. Otherwise, contact the Secretary.
        """

        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            if drop is None:
                await ctx.send(f'What is your name?')
                drop_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                drop = drop_msg.content.strip()
            if pick is None:
                await ctx.send(f'Who are you dropping it to?')
                pick_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                pick = pick_msg.content.strip()
            if day is None:
                await ctx.send(f'Which day? (1 for monday, 2 for tuesday, etc.)')
                day_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                day = day_msg.content.strip()
            if week is None:
                await ctx.send(f'Week number? (1, 2, etc.)')
                week_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                week = week_msg.content.strip()
            if classLevel is None:
                await ctx.send(f'Which level? (beg1, combat, etc.)')
                cl_msg = await self.bot.wait_for("message", check=check, timeout = 30.0)
                classLevel = cl_msg.content.strip()
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !dropto to restart")
            return

        drop = drop.upper()
        pick = pick.upper()
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

                    cursor = await db.execute("SELECT id FROM Coaches WHERE UPPER(name) = ?;", (drop,))
                    result = await cursor.fetchone()
                    if result is None:
                        await ctx.send(f"Coach {drop} is not found.")
                        return
                    
                    coach_a_id = result[0]

                    cursor = await db.execute("""SELECT id FROM Classes
                                              WHERE day = ?
                                              AND week = ?
                                              AND level = ?;""", (day, week, classLevel,))
                    result = await cursor.fetchone()
                    if result is None:
                        await ctx.send(f"Class D{day} W{week} L{classLevel} is not found.")
                        return
                    
                    class_id = result[0]

                    await db.execute(f"""UPDATE CoachClasses
                                     SET coach_id = ?
                                     WHERE coach_id = ?
                                     AND class_id = ?;""",
                                     (coach_b_id, coach_a_id, class_id,))
                    await self.bot.db.commit()
            else:
                await ctx.send("Cancelling request")
        except asyncio.TimeoutError:
            await ctx.send("You didn't reply in time, try !dropto to restart")
            return


async def setup(bot):
    await bot.add_cog(BotCog(bot))