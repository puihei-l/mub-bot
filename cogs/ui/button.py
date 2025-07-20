import discord
from discord.ui import View, Button

class ConfirmView(View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user
        self.value = None  # store if confirmed or not

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        self.value = True
        await interaction.response.send_message("Confirmed!", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction, button):
        if interaction.user != self.user:
            await interaction.response.send_message("This button is not for you!", ephemeral=True)
            return
        self.value = False
        await interaction.response.send_message("Cancelled!", ephemeral=True)
        self.stop()