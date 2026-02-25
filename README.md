# Terminal Trove Discord Bot

A powerful Discord bot designed to fetch, cache, and showcase the best terminal tools from [Terminal Trove](https://terminaltrove.com). Stay updated with the latest CLI utilities directly from your server.

---

## Features

* **Live Updates:** Automatically polls the Terminal Trove RSS feed every 60 minutes for new additions.
* **Tool of the Week (TOTW):** Scrapes and displays the featured "Tool of the Week," complete with GIF/Banner previews.
* **Smart Search:** Instantly find any tool on the site using a simple slash command.
* **Local Caching:** Stores tool metadata in `tool_cache.json` to reduce redundant scraping and speed up random searches.
* **Persistent Config:** Settings like `CHANNEL_ID` and `PING_ROLE_ID` are saved to `config.json` and survive bot restarts.
* **Interactive UI:** Paged embeds with navigation buttons for browsing large tool directories.

---

## Commands

| Command | Description |
| :--- | :--- |
| `/tools` | Shows all tools currently listed on Terminal Trove in a paged menu. |
| `/newtools` | Displays the 6 most recent additions to the directory. |
| `/totw` | Displays the current "Tool of the Week." |
| `/searchtool` | Search for a specific tool by its exact name. |
| `/randomtool` | Pulls a random terminal tool from the local cache. |
| `/setchannel` | **(Admin)** Sets the current channel for automated weekly updates. |
| `/setrole` | **(Admin)** Sets the role to be pinged when a new tool is detected. |

---

## Setup & Installation

### 1. Prerequisites
* Python 3.8 or higher
* A Discord Bot Token (via [Discord Developer Portal](https://discord.com/developers/applications))

### 2. Install Dependencies
Run the following command to install the required libraries:
```bash
pip install discord.py python-dotenv requests beautifulsoup4 colorama
```
