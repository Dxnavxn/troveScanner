import os
import discord                 # Third-party: The main Discord API wrapper
from discord.ext import commands ,tasks  # Third-party: To make the bot check the XML on a timer
from dotenv import load_dotenv
import xml.etree.ElementTree as ET # Standard: To parse and read your new.xml file
import requests                # Third-party: To download the XML if it's hosted online
import datetime                # Standard: To format the <updated> timestamps for Discord
from colorama import init, Fore
from zoneinfo import ZoneInfo

# ---------------- Logging ---------------- #
def log(message: str, level: str = "INFO") -> None:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {
        "INFO": Fore.CYAN,
        "SUCCESS": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
    }
    color = colors.get(level, "")
    print(color + f"[{timestamp}] [{level}] {message}")


# Initalize colorama
init(autoreset=True)

# Load Enviroment Variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
if not TOKEN:
    log("DISCORD_TOKEN is not set in the environment", "ERROR")
else: 
    log("DISCORD_TOKEN Loaded", "SUCCESS")


# ---------------- Defaults ---------------- #
DEFAULT_CHANNEL_ID: int = None 
DEFAULT_PING_ROLE_ID: int = None


# ---------------- Guild-Specific Config ---------------- #
# Stores channel_id and ping_role_id per guild
guild_configs: dict[int, dict[str, int | None]] = {}

# Eastern Timezone
EASTERN = ZoneInfo("America/New_York")

# ---------------- Bot Setup ---------------- #
intents = discord.Intents.default()  # message content intent not required
bot = commands.Bot(command_prefix="?", intents=intents)
tree = bot.tree

# ---------------- Helper Functions ---------------- #
async def getNewTools():
    """Fetch Terminal Trove 'New Tools' RSS"""
    url="https://terminaltrove.com/new.xml"

    respsone = requests.get(url)

    if respsone.status_code != 200:
        log(f"Cannot Fetch 'newTools' URL: <{url}>", "ERROR")
        return [] 
    else:
        log(f"'newTool' URL Loaded: <{url}>", "SUCCESS")

    root = ET.fromstring(respsone.content)


    # Define the Namespace (Required for Atom feeds)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    tools = []
    for entry in root.findall('atom:entry', ns):
        toolData = {
            "title": entry.find('atom:title',ns).text,
            "summary": entry.find('atom:summary',ns).text,
            "link": entry.find('atom:link', ns).get('href'),
            "updated": entry.find('atom:updated', ns ).text
        }
        tools.append(toolData)
    return tools

async def getToolOfTheWeek():
    """Fetch Terminal Trove 'Tool of The Week' RSS"""
    url = "https://terminaltrove.com/totw.xml"
    response = requests.get(url)

    if response.status_code != 200:
        log(f"Cannot Fetch 'toolOfTheWeek' URL: <{url}>", "ERROR")
        return []
    else:
        log(f"'toolOfTheWeek' URL Loaded: <{url}>", "SUCCESS")
    
    root = ET.fromstring(response.content)

    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    tools = []
    for entry in root.findall('atom:entry', ns ):
        toolData = {
            "title": entry.find('atom:title',ns).text,
            "summary": entry.find('atom:summary',ns).text,
            "link": entry.find('atom:link', ns).get('href'),
            "updated": entry.find('atom:updated', ns ).text
        }
        tools.append(toolData)
    return tools




# ---------------- Embed Creation ---------------- #
class CreateEmbed(discord.ui.View):
    def __init__(self, data, timeout=180, title="New Tool Board", description="", color=0xffffff):
        super().__init__(timeout=timeout)
        self.data = data  # You MUST store the data here to use it later
        self.titleText = title
        self.descText = description  
        self.color = color
        self.currentPage = 0
        self.perPage = 8 # 10 is very large for one embed; 5-8 is usually better
        self.end = (len(data) - 1) // self.perPage

    def createEmbed(self):
        start = self.currentPage * self.perPage
        end = start + self.perPage
        chunk = self.data[start:end]

        # Format the dictionaries into a readable string
        lines = []
        count = start + 1
        for tool in chunk:

            line = f"{count}> **[{tool['title']}]({tool['link']})** \n{tool['summary']}"
            lines.append(line)
            count += 1

        chunkDesc = "\n\n".join(lines)
        fullDescription = f"{self.descText}\n\n{chunkDesc}"

        embed = discord.Embed(
            title=f"{self.titleText}: Page {self.currentPage + 1}",
            description=fullDescription,
            color=self.color # Note: Use the integer directly
        )
        return embed
    
    def createSingleEmbed (self, index=0):
        """Embed for TOTW and Search command"""
        tool = self.data[index]

        embed = discord.Embed(
            title=f"**TOOL OF THE WEEK**: {tool['title']}",
            description=f"{tool['summary']}\n\n[View on Terminal Trove]({tool['link']})",
            color=0xF1C40F # Star Gold
        )
        embed.set_footer(text=f"Last Updated: {tool['updated']}")  

        return embed
    
    @discord.ui.button(label="«", style=discord.ButtonStyle.gray)
    async def firstPage(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.currentPage > 0:
            self.currentPage = 0
            await interaction.response.edit_message(embed=self.createEmbed(), view=self)
            log(f"{interaction.user.name.capitalize()} turned to page first page", "INFO")
        else:
            await interaction.response.send_message("You're on the first page!", ephemeral=True)
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prevButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.currentPage > 0:
            self.currentPage -= 1
            await interaction.response.edit_message(embed=self.createEmbed(), view=self)
            log(f"{interaction.user.name.capitalize()} turned to page {self.currentPage + 1}", "INFO")
        else:
            await interaction.response.send_message("You're on the first page!", ephemeral=True)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.green)
    async def nextButton(self, interaction: discord.Interaction, button: discord.ui.Button):
        # FIX: Check against self.end before incrementing
        if self.currentPage < self.end:
            self.currentPage += 1
            await interaction.response.edit_message(embed=self.createEmbed(), view=self)
            log(f"{interaction.user.name.capitalize()} turned to page {self.currentPage + 1}", "INFO")
        else:
            await interaction.response.send_message("You're on the last page!", ephemeral=True)

    @discord.ui.button(label="»", style=discord.ButtonStyle.green)
    async def lastPage(self, interaction: discord.Interaction, button: discord.ui.Button):
        # FIX: Check against self.end before incrementing
        if self.currentPage < self.end:
            self.currentPage = self.end
            await interaction.response.edit_message(embed=self.createEmbed(), view=self)
            log(f"{interaction.user.name.capitalize()} turned to last page {self.currentPage + 1}", "INFO")
        else:
            await interaction.response.send_message("You're on the last page!", ephemeral=True)

# ---------------- Commands ---------------- #
@tree.command(name="newtools", description="Shows the newest tools posted on 'terminaltrove.com/'")
async def newtools(interaction: discord.Interaction):
    await interaction.response.defer()

    # Get data
    tools = await getNewTools()
    if not tools:
        log("'newTools' not loaded", "ERROR")
        return await interaction.followup.send("Could not fetch tools at this time...")
    
    # Create and send embed
    view = CreateEmbed(data=tools, title="New Tools", color=0xff7ec1)
    embed = view.createEmbed()
    await interaction.followup.send(embed=embed, view=view)

@tree.command(name="totw", description="Shows the newest 'Tool Of The Week' (Updates every wednesday)")
async def totw(interaction: discord.Interaction):
    await interaction.response.defer() 

    tools = await getToolOfTheWeek()
    if not tools:
        return await interaction.followup.send("Could not fetch tools.")
    view = CreateEmbed(data=tools)
    await interaction.followup.send(embed=view.createSingleEmbed(0))



# ---------------- Bot Events ---------------- #

@bot.event
async def on_ready():
    log(f"Logged in as {bot.user} (ID: {bot.user.id})", "SUCCESS")
    
    # Sync Commands
    try:
        synced = await bot.tree.sync()
        log(f"Synced {len(synced)} slash commands", "INFO")
    except Exception as e:
        log(f"Failed to sync commands: {e}", "ERROR")

    tools = await getNewTools()
    log(f"Test Fetch Successful! Found {len(tools)} Tools", "INFO")

# ---------------- Run ---------------- #
def main():
    try:
        bot.run(TOKEN)
    except Exception as e:
        log(f"Failed to start bot: {e}", "ERROR")

if __name__ == "__main__":
    main()