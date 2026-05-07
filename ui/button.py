import discord
from discord.ui import View

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


class TransferApprovalView(View):
    def __init__(self, requester: discord.abc.User, acceptor: discord.abc.User):
        super().__init__(timeout=60)
        self.requester = requester
        self.acceptor = acceptor
        self.value = None  # True=approved, False=rejected

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve_button(self, interaction, button):
        if interaction.user != self.acceptor:
            await interaction.response.send_message("Only the receiving coach can approve.", ephemeral=True)
            return
        self.value = True
        await interaction.response.send_message("Approved.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject_button(self, interaction, button):
        if interaction.user != self.acceptor:
            await interaction.response.send_message("Only the receiving coach can reject.", ephemeral=True)
            return
        self.value = False
        await interaction.response.send_message("Rejected.", ephemeral=True)
        self.stop()