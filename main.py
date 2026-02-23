import os
import discord                 
from discord.ext import commands ,tasks  
from dotenv import load_dotenv
import xml.etree.ElementTree as ET 
import requests                
import datetime         
import json
import random
from colorama import init, Fore
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

# ---------------- Logging ---------------- # 
# SHOUTOUT EIGHTBY8
def log(message: str, level: str = "INFO") -> None:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    colors = {
        "INFO": Fore.CYAN,
        "SUCCESS": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "RANDOM TOOL": Fore.MAGENTA,
        "SEARCH TOOL": Fore.MAGENTA,
        "NEW TOOL": Fore.MAGENTA,
        "TOTW": Fore.MAGENTA,
        "SEARCH": Fore.MAGENTA
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

# ---------------- Cache ---------------- #
lastToolCache = {} # Stores tools for commands


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
        log(f"'newTool' URL Found", "SUCCESS")

    root = ET.fromstring(respsone.content)


    # Define the Namespace (Required for Atom feeds)
    ns = {'atom': 'http://www.w3.org/2005/Atom'}

    tools = []
    for entry in root.findall('atom:entry', ns):
        toolData = {
            "title": entry.find('atom:title',ns).text,
            "summary": entry.find('atom:summary',ns).text,
            "link": entry.find('atom:link', ns).get('href'),
            # "updated": entry.find('atom:updated', ns ).text
        }
        tools.append(toolData)
    return tools

async def getToolOfTheWeek():
    """Fetch Terminal Trove 'Tool of The Week' from HTML"""
    url = "https://terminaltrove.com/tool-of-the-week/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            log(f"Cannot Fetch 'toolOfTheWeek' URL: <{url}>", "ERROR")
            return []
        
        log(f"'toolOfTheWeek' URL Loaded", "SUCCESS")
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        mainContent = soup.find('main')
        if not mainContent:
            log("Could not find <main> content for TOTW", "ERROR")
            return []

        # Find the main visual (Banner or GIF)
        picUrl = None
        for img in mainContent.find_all('img'):
            src = img.get('src', '')
            if any(src.endswith(ext) for ext in ['.png','.jpg']):
                picUrl = f"https://terminaltrove.com{src}" if src.startswith('/') else src
                log("'toolOfTheWeek' PNG Found", "SUCCESS")
                break
            else:
                picUrl = f"https://terminaltrove.com{src}" if src.startswith('/') else src
                log("'toolOfTheWeek' GIF Found", "SUCCESS")
                break

        
        # Grab the title (usually in an h1 or h2 inside main)
        titleEl = mainContent.find('h2')
        title = titleEl.get_text(strip=True) if titleEl else "Tool of the Week"
        
        # Grab the first paragraph for the description
        summaryEl = mainContent.find('small')
        summary = summaryEl.get_text(strip=True) if summaryEl else "No description available."

        results.append({
            "title": title,
            "summary": summary,
            "link": url,
            "gif": picUrl, # Keeping key 'gif' so it works with searchEmbed()
            "updated": datetime.datetime.now().strftime("%Y-%m-%d")
        })
        
        return results

    except Exception as e:
        log(f"TOTW Scrape Error: {e}", "ERROR")
        return []
    
    # Searches tool_cahce.json for tools 
async def scrapeSearch(query: str):
    cleanQuery = query.lower().replace(" ", "-").strip("/")
    url = f"https://terminaltrove.com/{cleanQuery}/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Find the Image (Priority: GIF > PNG)
        picUrl = None
        main_content = soup.find('main')
        if main_content:
            all_imgs = main_content.find_all('img')
            img_srcs = [img.get('src', '') for img in all_imgs]

            # Extract Title and Tagline (with fallbacks)
            title_el = soup.find('h1')
            title = title_el.get_text(strip=True) if title_el else query.capitalize()
                        
                # Check for GIF first
            for src in img_srcs:
                if src.endswith('.gif'):
                    picUrl = f"https://terminaltrove.com{src}" if src.startswith('/') else src
                    break
            
            # If no GIF, check for PNG
            if not picUrl:
                for src in img_srcs:
                    if src.endswith('.png'):
                        picUrl = f"https://terminaltrove.com{src}" if src.startswith('/') else src
                        break

            if picUrl:
                if picUrl.endswith('.gif'):
                    log(f"GIF found for <{title}>", "SUCCESS")
                else:
                    log(f"PNG found for <{title}>", "SUCCESS")
            else:
                log(f"No image found for <{title}>", "WARNING")


        tagline_el = soup.find('p', id='tagline')
        tagline = tagline_el.get_text(strip=True) if tagline_el else "Terminal tool found on Terminal Trove."

        results.append({
            "title": title,
            "summary": tagline,
            "link": url,
            "updated": "Direct Match",
            "gif": picUrl
        })
        
        return results
        
    except Exception as e:
        log(f"Search error: {e}", "ERROR")
        return []
    
def updateCache(newData):
    # Load the existing tools from the file if it exists
    try:
        with open('tool_cache.json', 'r') as f:
            oldData = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file doesn't exist, start with an empty list
        oldData = []

    #  Extract just the titles so we can check for duplicates
    existingTitles = {tool['title'] for tool in oldData}

    #  Only add tools that we haven't seen before
    addedCount = 0
    for tool in newData:
        if tool['title'] not in existingTitles:
            oldData.append(tool)
            addedCount += 1

    #  Save the combined list back to the file
    with open('tool_cache.json', 'w') as f:
        json.dump(oldData, f, indent=4)
    
    if addedCount == 0:
        log(f"Cache Up to date. Total: {len(oldData)} tools ")
    else:
        log(f"Cache Updated: Added {addedCount} new tools. Total: {len(oldData)}", "SUCCESS")



# ---------------- UI / Embed Creation ---------------- #
class CreateEmbed(discord.ui.View):
    def __init__(self, data, timeout=180, title="New Tool Board", description="", color=0xffffff):
        super().__init__(timeout=timeout)
        self.data = data
        self.titleText = title
        self.descText = description  
        self.color = color
        self.currentPage = 0
        self.perPage = 8 
        self.end = (len(data) - 1) // self.perPage

    # Paged Embed
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
            color=self.color 
        )
        return embed
    
    
    def searchEmbed(self, index=0):
        tool = self.data[index]
        
        embed = discord.Embed(
            title=f"TOOL FOUND: {tool['title']}",
            description=f"{tool['summary']}\n\n[View on Terminal Trove]({tool['link']})",
            color=0x89d672
        )
        
        if tool.get('gif'):
            embed.set_image(url=tool['gif'])
                    
        embed.set_footer(text="lol")
        return embed
    
    def totwEmbed (self, index=0):
        """Embed for TOTW and Search command"""
        tool = self.data[index]

        embed = discord.Embed(
            title=f"**TOOL OF THE WEEK**: {tool['title']}",
            description=f"{tool['summary']}\n\n[View on Terminal Trove]({tool['link']})",
            color=0xF1C40F 
        )
        embed.set_footer(text=f"Last Updated: {tool['updated']}") 
        
        if tool.get('gif'):
            embed.set_image(url=tool['gif']) 

        return embed
    
    def randomEmbed(self, index=0):
        tool = self.data[index]

        embed = discord.Embed(
            title=f"**RANDOM TOOL**: {tool['title']}",
            description=f"{tool['summary']}\n\n[View on Terminal Trove]({tool['link']})",
            color=0xf8be16
        )
        
        if tool.get('gif'):
            embed.set_image(url=tool['gif'])
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
        if self.currentPage < self.end:
            self.currentPage += 1
            await interaction.response.edit_message(embed=self.createEmbed(), view=self)
            log(f"{interaction.user.name.capitalize()} turned to page {self.currentPage + 1}", "INFO")
        else:
            await interaction.response.send_message("You're on the last page!", ephemeral=True)

    @discord.ui.button(label="»", style=discord.ButtonStyle.green)
    async def lastPage(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    log(f"'newTools' Called by {interaction.user.name.capitalize()}", "NEW TOOL")
    # Get data   
    tools = await getNewTools()
    if not tools:
        log("'newTools' not loaded", "ERROR")
        return await interaction.followup.send("Could not fetch tools at this time...")
    updateCache(tools)
    
    # Create and send embed
    view = CreateEmbed(data=tools, title="New Tools", color=0xff7ec1)
    embed = view.createEmbed()
    log(f"'newTools' Posted by {interaction.user.name.capitalize()}","NEW TOOL")
    await interaction.followup.send(embed=embed, view=view)

@tree.command(name="totw", description="Shows the newest 'Tool Of The Week' (Updates every wednesday)")
async def totw(interaction: discord.Interaction):
    await interaction.response.defer() 

    log(f"'toolOfTheWeek' Called by {interaction.user.name.capitalize()}", "TOTW")
    tools = await getToolOfTheWeek()
    if not tools:
        log(f"Unable to post 'toolOfTheWeek' Embed", "TOTW")
        return await interaction.followup.send("Could not fetch tools.")
    view = CreateEmbed(data=tools) 
    
    log(f"'toolOfTheWeek' Posted by {interaction.user.name.capitalize()} ","TOTW")
    await interaction.followup.send(embed=view.totwEmbed(0))    
    
@tree.command(name="searchtool", description="Find a specific tool by its exact name")
@discord.app_commands.describe(query="The exact name of the tool (e.g., act3)")
async def searchTool(interaction: discord.Interaction, query: str):
    await interaction.response.defer()
    log(f"'searchTool' Called by {interaction.user.name.capitalize()} | Query: <{query}>", "SEARCH")
    results = await scrapeSearch(query)
    
    if not results:
        log(f"Search failed for '{query}'", "SEARCH")
        return await interaction.followup.send(
            f"**{query}** was not found. Check the spelling or try /newtools to refresh the cache!", 
            ephemeral=True
        )

    view = CreateEmbed(data=results)

    log(f"'searchTool' posted by {interaction.user.name.capitalize()}","SEARCH")
    await interaction.followup.send(embed=view.searchEmbed(0))
    
    # Save to cache so /randomtool can use this GIF later without scraping!
    updateCache(results)

@tree.command(name="randomtool", description="Find a random terminal tool from Terminaltrove.com")
async def randomTool(interaction: discord.Interaction):
    try:
        with open('tool_cache.json', 'r') as f:
            tools = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log("Unable to post 'randomTool")
        return await interaction.response.send_message("Cache is empty! Run /newtools.", ephemeral=True)
    
    toolChoice = random.choice(tools)
    log(f"'randomTool' ran by {interaction.user.name.capitalize()} | TOOL: '{toolChoice["title"]}'", "RANDOM TOOL")

    if 'gif' not in toolChoice or not toolChoice['gif']:
        await interaction.response.defer() 
        
        scrapedData = await scrapeSearch(toolChoice['title'])
        if scrapedData:
            toolChoice['gif'] = scrapedData[0].get('gif')

        view = CreateEmbed(data=[toolChoice])
        await interaction.followup.send(embed=view.randomEmbed(0))
        log(f"'randomTool' posted by {interaction.user.name.capitalize()}", "RANDOM TOOL")
    
    else:
        view = CreateEmbed(data=[toolChoice])
        await interaction.response.send_message(embed=view.randomEmbed(0))
        log("Posted without GIF","RANDOM TOOL")




# ---------------- Bot Events ---------------- #
@bot.event
async def on_ready():
    log(f"Logged in as {bot.user} (ID: {bot.user.id}) ", "SUCCESS")
    
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