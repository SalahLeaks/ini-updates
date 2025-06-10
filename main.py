import os
import io
import json
import math
import asyncio
import aiohttp
import discord
from discord import File, Embed
from dotenv import load_dotenv
from datetime import datetime, timedelta
import re
import logging

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[Logs] %(message)s'
)

DEVICE_ID      = os.getenv("EPIC_DEVICE_ID")
DEVICE_SECRET  = os.getenv("EPIC_DEVICE_SECRET")
ACCOUNT_ID     = os.getenv("EPIC_ACCOUNT_ID")
CLIENT_SECRET  = os.getenv("EPIC_CLIENT_SECRET")
TOKEN_URL      = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"
SYSTEM_API_URL = "https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/cloudstorage/system"

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID    = int(os.getenv("DISCORD_CHANNEL_ID", "YOUR_CHANNEL_ID"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
STATE_DIR     = "state"
os.makedirs(STATE_DIR, exist_ok=True)


class FortniteTrackerBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.access_token     = None
        self.refresh_token    = None
        self.token_expires_at = datetime.utcnow()
        self.filename_map     = {}
        self.endpoints        = []

    async def on_ready(self):
        logging.info("Bot is online and ready.")
        # Fetch dynamic list of files
        await self.load_file_list()
        asyncio.create_task(self.poll_loop())

    async def load_file_list(self):
        logging.info("Fetching system file list…")
        text = await self.fetch_json(SYSTEM_API_URL)
        data = json.loads(text)
        # Build mapping and endpoint URLs
        for entry in data:
            ufn = entry.get("uniqueFilename")
            fname = entry.get("filename")
            if ufn and fname:
                self.filename_map[ufn] = fname
                self.endpoints.append(f"{SYSTEM_API_URL}/{ufn}")
        logging.info(f"Loaded {len(self.endpoints)} files to track.")

    async def device_auth(self):
        data = {
            "grant_type":   "device_auth",
            "device_id":    DEVICE_ID,
            "secret":       DEVICE_SECRET,
            "account_id":   ACCOUNT_ID
        }
        headers = {
            "Content-Type":  "application/x-www-form-urlencoded",
            "Authorization": f"Basic {CLIENT_SECRET}"
        }
        async with aiohttp.ClientSession() as sess:
            resp = await sess.post(TOKEN_URL, data=data, headers=headers)
            resp.raise_for_status()
            j = await resp.json()
            logging.info("Obtained new device refresh token.")
            return j["refresh_token"]

    async def refresh_access_token(self):
        if not self.refresh_token:
            self.refresh_token = await self.device_auth()
        data = {
            "grant_type":    "refresh_token",
            "refresh_token": self.refresh_token,
            "token_type":    "eg1"
        }
        headers = {
            "Content-Type":     "application/x-www-form-urlencoded",
            "Authorization":    f"Basic {CLIENT_SECRET}",
            "X-Epic-Device-ID": "device_auth"
        }
        async with aiohttp.ClientSession() as sess:
            resp = await sess.post(TOKEN_URL, data=data, headers=headers)
            resp.raise_for_status()
            j = await resp.json()
            self.access_token     = j["access_token"]
            self.token_expires_at = datetime.utcnow() + timedelta(minutes=14)
            logging.info("Refreshed access token.")

    async def fetch_json(self, url):
        if not self.access_token or datetime.utcnow() >= self.token_expires_at:
            await self.refresh_access_token()
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent":    "Mozilla/5.0"
        }
        async with aiohttp.ClientSession() as sess:
            resp = await sess.get(url, headers=headers)
            if resp.status == 401:
                logging.info("Access token expired, refreshing…")
                await self.refresh_access_token()
                headers["Authorization"] = f"Bearer {self.access_token}"
                resp = await sess.get(url, headers=headers)
            resp.raise_for_status()
            return await resp.text()

    # parsing helpers unchanged...
    def _parse_hotfix_strings(self, lines):
        pat = re.compile(
            r'\+TextReplacements=.*?Key="(?P<k>[^"]+)".*?LocalizedStrings=\(\((?P<i>.+?)\)\)\)\n'
        )
        en = re.compile(r'\("en","(?P<t>[^"]+)"\)')
        out = []
        for l in lines:
            m = pat.search(l)
            if not m:
                continue
            inner = m.group("i")
            m2 = en.search(inner)
            if m2:
                out.append((m.group("k"), m2.group("t")))
        return out

    def _parse_datatable(self, lines, sign):
        # identical to before...
        out = []
        for l in lines:
            if f"{sign}DataTable=" not in l:
                continue
            body = l.lstrip(f"{sign} ").rstrip()
            try:
                _, rest = body.split("=", 1)
            except ValueError:
                continue
            parts = rest.split(";", 4)
            if len(parts) == 5:
                path, action, row, field, value = parts
                out.append((path, row, field, value, sign))
            elif len(parts) == 3:
                path, action, inner = parts
                if action == "AddRow":
                    try:
                        inner_content = inner[1:-1] if (inner.startswith('"') and inner.endswith('"')) else inner
                        data = json.loads(inner_content)
                        row_name = data.get("Name", "")
                        wrapped_str = data.get("WrappedString", "")
                        out.append((path, row_name, "WrappedString", wrapped_str, sign))
                    except json.JSONDecodeError:
                        logging.warning(f"[parse_datatable] JSON‐decode failed: {inner}")
                elif action == "TableUpdate":
                    try:
                        inner_content = inner[1:-1] if (inner.startswith('"') and inner.endswith('"')) else inner
                        data_list = json.loads(inner_content)
                        for entry in data_list:
                            name = entry.get("Name","")
                            ti_obj = entry.get("TaskIdentifier",{})
                            task_tag = ti_obj.get("TagName","") if isinstance(ti_obj,dict) else ""
                            link = entry.get("LinkedQuestDefinition","")
                            out.append((path,name,"TaskIdentifier.TagName",task_tag,sign))
                            out.append((path,name,"LinkedQuestDefinition",link,sign))
                    except json.JSONDecodeError:
                        logging.warning(f"[parse_datatable] JSON‐decode failed: {inner}")
        return out

    def _parse_curvetable(self, lines, sign):
        # identical to before...
        out = []
        for l in lines:
            if f"{sign}CurveTable=" not in l:
                continue
            body = l.lstrip(f"{sign} ").rstrip()
            try:
                _, rest = body.split("=",1)
            except ValueError:
                continue
            parts = rest.split(";",4)
            if len(parts) < 5:
                continue
            path, action, identifier, input_val, new_val = parts
            if "." not in identifier:
                continue
            row, field = identifier.rsplit(".",1)
            out.append((path, row, field, new_val, sign))
        return out

    async def send_embed_safe(self, channel, embed, file=None):
        try:
            await channel.send(embed=embed, file=file)
            logging.info("Message sent successfully")
        except discord.HTTPException as he:
            msg = str(he).lower()
            if "embeds too large" in msg or "maximum number of embeds" in msg:
                fields = embed.fields
                chunks = [fields[i:i+5] for i in range(0,len(fields),5)]
                for idx, chunk in enumerate(chunks,1):
                    part = Embed(title=f"{embed.title} (part {idx}/{len(chunks)})")
                    for f in chunk:
                        part.add_field(name=f.name, value=f.value, inline=f.inline)
                    try:
                        await channel.send(embed=part)
                    except Exception:
                        pass
        except Exception:
            pass

    async def poll_loop(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)
        logging.info(f"Starting poll loop against {len(self.endpoints)} endpoints.")

        while True:
            logging.info("Fetching data from Cloud Storage endpoints…")
            for url in self.endpoints:
                key           = url.rsplit("/", 1)[-1]
                friendly_name = self.filename_map.get(key, key)
                state_file    = os.path.join(STATE_DIR, f"{friendly_name}.json")

                try:
                    text = await self.fetch_json(url)
                except Exception as e:
                    logging.info(f"[{friendly_name}] fetch error: {e} — skipping")
                    continue

                new_lines = text.splitlines(keepends=True)
                old_lines = []
                if os.path.isfile(state_file):
                    with open(state_file, "r", encoding="utf-8") as f:
                        old_lines = json.load(f)

                added   = [l for l in new_lines if l not in old_lines]
                removed = [l for l in old_lines if l not in new_lines]

                if not (added or removed):
                    logging.info(f"[{friendly_name}] No changes found.")
                    continue

                logging.info(f"Change found in {friendly_name} (+{len(added)}/-{len(removed)}) — processing")

                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(new_lines, f, indent=2)

                dt_plus       = self._parse_datatable(added, "+")
                dt_minus      = self._parse_datatable(removed, "-")
                ct_plus       = self._parse_curvetable(added, "+")
                ct_minus      = self._parse_curvetable(removed, "-")
                hotfixes_plus = self._parse_hotfix_strings(added)

                diff_payload = {"added": added, "removed": removed}
                diff_bytes   = json.dumps(diff_payload, indent=2).encode("utf-8")
                diff_file    = File(fp=io.BytesIO(diff_bytes), filename=f"{friendly_name}_diff.json")

                total_parsed = (
                    len(hotfixes_plus)
                    + len(dt_plus)
                    + len(dt_minus)
                    + len(ct_plus)
                    + len(ct_minus)
                )

                if total_parsed == 0:
                    count_embed = Embed(title=f"Parsed Updates in {friendly_name}")
                    count_embed.add_field(name="Strings",     value="0", inline=True)
                    count_embed.add_field(name="DataTables",  value="0", inline=True)
                    count_embed.add_field(name="CurveTables", value="0", inline=True)
                    count_embed.add_field(name="Total Mods",  value="0", inline=False)

                    await self.send_embed_safe(channel, count_embed, file=diff_file)
                    logging.info(f"No parsed mods; sent raw diff JSON for {friendly_name}.")
                    continue

                embeds = []

                # DataTable embeds
                dt_changes = dt_plus + dt_minus
                if dt_changes:
                    by_path = {}
                    for path, row, field, val, sign in dt_changes:
                        by_path.setdefault(path, []).append((row, field, val, sign))
                    for path, mods in by_path.items():
                        num_parts = math.ceil(len(mods)/25)
                        for pi in range(num_parts):
                            chunk = mods[pi*25:(pi+1)*25]
                            e = Embed(title="Summary")
                            e.description = f"➥ **DataTable Modification:** ```{path}```"
                            for row, field, val, sign in chunk:
                                e.add_field(name=f"`{row} → {field}`", value=val, inline=False)
                            embeds.append(e)

                # CurveTable embeds
                ct_changes = ct_plus + ct_minus
                if ct_changes:
                    by_path = {}
                    for path, row, field, val, sign in ct_changes:
                        by_path.setdefault(path, []).append((row, field, val, sign))
                    for path, mods in by_path.items():
                        num_parts = math.ceil(len(mods)/25)
                        for pi in range(num_parts):
                            chunk = mods[pi*25:(pi+1)*25]
                            e = Embed(title="Summary")
                            e.description = f"```{path}```"
                            for row, field, val, sign in chunk:
                                e.add_field(name=f"`{row}.{field}`", value=val, inline=False)
                            embeds.append(e)

                # Hotfix strings embeds
                if hotfixes_plus:
                    num_parts = math.ceil(len(hotfixes_plus)/25)
                    for pi in range(num_parts):
                        chunk = hotfixes_plus[pi*25:(pi+1)*25]
                        e = Embed(title="Summary")
                        e.description = "➥ **String modification detected**"
                        for key, text in chunk:
                            e.add_field(name=f"**{key}**", value=f"➥ {text}", inline=False)
                        embeds.append(e)

                # Summary count embed
                count_embed = Embed(title=f"Parsed Updates in {friendly_name}")
                count_embed.add_field(name="Strings",     value=str(len(hotfixes_plus)), inline=True)
                count_embed.add_field(name="DataTables",  value=str(len(dt_plus)),         inline=True)
                count_embed.add_field(name="CurveTables", value=str(len(ct_plus)),         inline=True)
                total_mods = (
                    len(hotfixes_plus)
                    + len(dt_plus)
                    + len(dt_minus)
                    + len(ct_plus)
                    + len(ct_minus)
                )
                count_embed.add_field(name="Total Mods", value=str(total_mods), inline=False)

                parsed_path = os.path.join(STATE_DIR, f"{friendly_name}_parsed.json")
                with open(parsed_path, "w", encoding="utf-8") as f:
                    json.dump([{
                        "section_name": friendly_name,
                        "modifications": [
                            *[{"type":"String","key":k,"value":t} for k,t in hotfixes_plus],
                            *[{"type":"DataTable","path":p,"row_name":r,"field":f,"new_value":v,"change":("Added" if s=="+" else "Removed")} for p,r,f,v,s in dt_plus+dt_minus],
                            *[{"type":"CurveTable","path":p,"row_name":r,"field":f,"new_value":v,"change":("Added" if s=="+" else "Removed")} for p,r,f,v,s in ct_plus+ct_minus],
                        ]
                    }], f, indent=4, ensure_ascii=False)

                with open(parsed_path, "rb") as fp:
                    parsed_file = File(fp, filename=os.path.basename(parsed_path))

                # Send in chunks of up to 10 embeds
                all_embeds = embeds + [count_embed]
                for i in range(0, len(all_embeds), 10):
                    chunk = all_embeds[i:i+10]
                    if i+10 >= len(all_embeds):
                        await channel.send(embeds=chunk, file=parsed_file)
                    else:
                        await channel.send(embeds=chunk)

                logging.info(f"Sent update for {friendly_name} (+{len(added)}/-{len(removed)})")

            logging.info(f"Waiting {POLL_INTERVAL}s before next poll")
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    bot = FortniteTrackerBot()
    bot.run(DISCORD_TOKEN)