import os
import io
import json
import asyncio
import aiohttp
import discord
from discord import File, Embed
from dotenv import load_dotenv
from datetime import datetime, timedelta
import re
import logging

load_dotenv()

# ——— CLEAN LOGGING SETUP ———
logging.basicConfig(
    level=logging.INFO,
    format='[Logs] %(message)s'
)

DEVICE_ID      = os.getenv("EPIC_DEVICE_ID")
DEVICE_SECRET  = os.getenv("EPIC_DEVICE_SECRET")
ACCOUNT_ID     = os.getenv("EPIC_ACCOUNT_ID")
CLIENT_SECRET  = os.getenv("EPIC_CLIENT_SECRET")
TOKEN_URL      = "https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token"

FILENAME_ENTRIES = [
    {"uniqueFilename": "e000dd0687b34cffa247532a8d7e4fd0", "filename": "Switch_RuntimeOptions.ini"},
    {"uniqueFilename": "93f93825f97a48739ea8761983eae344", "filename": "DefaultHardware.ini"},
    {"uniqueFilename": "f9d8df13a971457aa587310f5677715e", "filename": "Helios_Game.ini"},
    {"uniqueFilename": "fc32184f109f47df9b71da7eebd11e4d", "filename": "IOS_Game.ini"},
    {"uniqueFilename": "919e99607d9f4e92b34b9a0a14cbe8ad", "filename": "HeliosMobile_RuntimeOptions.ini"},
    {"uniqueFilename": "28380724efe7440dbb81a6e020c33f8e", "filename": "Android_Game.ini"},
    {"uniqueFilename": "f51be88fb63944d981fb17e9e8a011aa", "filename": "HeliosMobile_Engine.ini"},
    {"uniqueFilename": "8127e4ae4beb4438b7d18df0c4c842f8", "filename": "PS5_DeviceProfiles.ini"},
    {"uniqueFilename": "a8e2eec195754563a9c8c559dc7d7a8b", "filename": "ValkyrieFortniteEditorEarlyAccessPermissions.json"},
    {"uniqueFilename": "ea6af556c11c4345b286ad69d4a57dbb", "filename": "MacClient_RuntimeOptions.ini"},
    {"uniqueFilename": "74fc422917244c5b97ad8189f4226a3c", "filename": "ValkyrieEditorConfig-FortniteGFS.json"},
    {"uniqueFilename": "de74e4fc39a147339df12f324d9201f4", "filename": "SproutNativeEngine.ini"},
    {"uniqueFilename": "75546d2569d94f9c9a9caff7e290c48b", "filename": "XB1_DeviceProfiles.ini"},
    {"uniqueFilename": "4076f7d595cc432fa6bb9d8694adcf2e", "filename": "PS4_Game.ini"},
    {"uniqueFilename": "6c33ead15c254f0da675c8c5aef79e84", "filename": "XB1_RuntimeOptions.ini"},
    {"uniqueFilename": "3f9feaebb56043bc9792b0805a821a8d", "filename": "PS4_RuntimeOptions.ini"},
    {"uniqueFilename": "c0de0ad59f634afa8fb7536183b43d44", "filename": "MacClient_Game.ini"},
    {"uniqueFilename": "72ef70a2781240a7a922a1aa3e34c87f", "filename": "WindowsEngine.ini"},
    {"uniqueFilename": "73e12b1bfbdd4e8a9a43336746278a3a", "filename": "GFN_RuntimeOptions.ini"},
    {"uniqueFilename": "dbfa6466d8a345ebb1ece39b5609c9f0", "filename": "XB1JunoGameNativeDeviceProfiles.ini"},
    {"uniqueFilename": "d16053edfaa74782b72283b51e7d393f", "filename": "DefaultFigmentCoreGame.ini"},
    {"uniqueFilename": "e3978add72f649fb81a67a1b7ad89445", "filename": "GFNMobile_RuntimeOptions.ini"},
    {"uniqueFilename": "311cc2f8c6fa4998b2f115ac52a70f9c", "filename": "XSXJunoGameNativeDeviceProfiles.ini"},
    {"uniqueFilename": "ba905cc6a853447fb5d6cf41b0ec68d0", "filename": "DefaultEditor.ini"},
    {"uniqueFilename": "fdd7170801c54f08afb89d090dffb5f9", "filename": "LunaMobile_Engine.ini"},
    {"uniqueFilename": "ee3aa8eba49c4a37a635d3231becad1e", "filename": "SwitchJunoGameNativeDeviceProfiles.ini"},
    {"uniqueFilename": "5211a1dbda8c422d940de277ff124585", "filename": "DefaultSproutTG_RiotFly_Gameplay.ini"},
    {"uniqueFilename": "3ac3b63afdee4a45b087811deb7678c4", "filename": "PS4_DeviceProfiles.ini"},
    {"uniqueFilename": "8987f8d84da848c5accc7fccb80fbe0d", "filename": "Helios_RuntimeOptions.ini"},
    {"uniqueFilename": "8f29d8be2d1c464eb51b16f41f406a0d", "filename": "PS4JunoGameNativeDeviceProfiles.ini"},
    {"uniqueFilename": "6d41966083cd4793842726e20c3b549e", "filename": "Scalability.ini"},
    {"uniqueFilename": "b33eeb3757ae4a54b1fd10e8be630c0a", "filename": "LunaMobile_RuntimeOptions.ini"},
    {"uniqueFilename": "b800b911053c4906a5bd399f46ae0055", "filename": "WindowsClient_RuntimeOptions.ini"},
    {"uniqueFilename": "c4d901de2aa5427f85734b6a85aa2000", "filename": "DeviceProfiles.ini"},
    {"uniqueFilename": "b6c60402a72e4081a6a47c641371c19f", "filename": "WindowsClient_Engine.ini"},
    {"uniqueFilename": "508f91af3aa6498c915202b7be1714dd", "filename": "DefaultJunoGameGame.ini"},
    {"uniqueFilename": "6549646f938f41f0b265173a358fb495", "filename": "GFN_Engine.ini"},
    {"uniqueFilename": "05222e1e3b1c4cdf8b9bd4cc5ac8e474", "filename": "XB1_Game.ini"},
    {"uniqueFilename": "57122528c65b445cb8c44709b096b1ed", "filename": "XSX_DeviceProfiles.ini"},
    {"uniqueFilename": "b1a172e4fdd746dc8815d61d379f198f", "filename": "PS5_RuntimeOptions.ini"},
    {"uniqueFilename": "15326849197846eab3fd92a3aaa59b9e", "filename": "XSX_Scalability.ini"},
    {"uniqueFilename": "430b3d85a2024f81b6fb4fb4d20f12ed", "filename": "XSX_Game.ini"},
    {"uniqueFilename": "4c4c823bbf9c4b0db6247e7ab36d37ab", "filename": "DefaultFigmentCoreEngine.ini"},
    {"uniqueFilename": "b22d3cad8e4f4ceeb5c55442f691b165", "filename": "Switch_Engine.ini"},
    {"uniqueFilename": "dc4ff873db7b4d93bcf72014bbbaa4b9", "filename": "PS4_Engine.ini"},
    {"uniqueFilename": "c52c1f9246eb48ce9dade87be5a66f29", "filename": "DefaultRuntimeOptions.ini"},
    {"uniqueFilename": "e9f237bed0d24a878c2132607831ff0c", "filename": "DefaultSpatialMetrics.ini"},
    {"uniqueFilename": "b6a9b64b52d14e60bf59360b41b119c9", "filename": "WindowsClient_DeviceProfiles.ini"},
    {"uniqueFilename": "1d773864100a4f53aac1eedf2eb3c332", "filename": "DefaultServiceBackup.ini"},
    {"uniqueFilename": "bac36c922b2f4ebe96a47d4bd6ebd05c", "filename": "DefaultSproutCoreEngine.ini"},
    {"uniqueFilename": "7d524f65b03a49b88d3e5d5268480f1f", "filename": "ValkyrieFortniteEditorPermissions.json"},
    {"uniqueFilename": "eedca963133e4c959bef113bff80b8e8", "filename": "DefaultJunoGameNativeEngine.ini"},
    {"uniqueFilename": "bbb036613a204f78a36a4653bf5e6bd0", "filename": "LunaMobile_Game.ini"},
    {"uniqueFilename": "c8a801897ec04667973d4f12f4b12399", "filename": "PS5_Scalability.ini"},
    {"uniqueFilename": "dc24c42ffe9a4cc5ae3a9946b4e5e95c", "filename": "PS5_Engine.ini"},
    {"uniqueFilename": "248d9bec1311419b81f08df4e1473940", "filename": "PS5JunoGameNativeDeviceProfiles.ini"},
    {"uniqueFilename": "7e2a66ce68554814b1bd0aa14351cd71", "filename": "WindowsClient_Game.ini"},
    {"uniqueFilename": "600a5f12fdfd491dbe8ffb62a3d8a8cb", "filename": "HeliosMobile_Game.ini"},
    {"uniqueFilename": "1c7eb1831955468f949854f706ed542c", "filename": "DefaultPartnerLimeGFSEngine.ini"},
    {"uniqueFilename": "3460cbe1c57d4a838ace32951a4d7171", "filename": "DefaultEngine.ini"},
    {"uniqueFilename": "494983533c8d4cc38d3f3cd3c81f75f4", "filename": "GFNMobile_Game.ini"},
    {"uniqueFilename": "6ad739ad7483464eb6448710cba4cf1e", "filename": "SwitchSproutNativeEngine.ini"},
    {"uniqueFilename": "ea95a5ff1474476f8ce9f0c500dd040b", "filename": "DefaultLimeGFSEngine.ini"},
    {"uniqueFilename": "6eab62f6409e490b871e5c509503c579", "filename": "Android_RuntimeOptions.ini"},
    {"uniqueFilename": "1858cde1df144e51a71733207c4968af", "filename": "GFN_Game.ini"},
    {"uniqueFilename": "532dc6866ade40c7b2f69fb2c9b5b3a0", "filename": "AndroidJunoGameNativeDeviceProfiles.ini"},
    {"uniqueFilename": "31ef7bccad1c4471a9de0939e0c64e86", "filename": "DefaultDelMarGameEngine.ini"},
    {"uniqueFilename": "b175cde10a9a420f8e151bade9d33918", "filename": "Luna_Game.ini"},
    {"uniqueFilename": "a22d837b6a2b46349421259c0a5411bf", "filename": "DefaultGame.ini"},
    {"uniqueFilename": "8d3fbfa671c4402080749368d556aa9", "filename": "IOS_RuntimeOptions.ini"},
    {"uniqueFilename": "f8b471a6ab4249ca4cd661dcfb957b2", "filename": "Luna_Engine.ini"},
    {"uniqueFilename": "13eb6542dda140d9aceeb5f25f92a2ed", "filename": "SproutJobs_BaseGame.ini"},
]
BASE_URL     = "https://fngw-mcp-gc-livefn.ol.epicgames.com/fortnite/api/cloudstorage/system/"
ENDPOINTS    = [BASE_URL + e["uniqueFilename"] for e in FILENAME_ENTRIES]
FILENAME_MAP = {e["uniqueFilename"]: e["filename"] for e in FILENAME_ENTRIES}

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID    = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "60"))
STATE_DIR     = "state"
os.makedirs(STATE_DIR, exist_ok=True)

class FortniteTrackerBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.access_token     = None
        self.refresh_token    = None
        self.token_expires_at = datetime.utcnow()

    async def on_ready(self):
        logging.info("Bot is online and ready.")
        asyncio.create_task(self.poll_loop())

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
        out = []
        for l in lines:
            if f"{sign}DataTable=" not in l:
                continue
            body = l.lstrip(f"{sign} ").rstrip()
            _, rest = body.split("=", 1)
            path, action, row, field, value = rest.split(";", 4)
            out.append((path, row, field, value, sign))
        return out

    def _parse_curvetable(self, lines, sign):
        out = []
        for l in lines:
            if f"{sign}CurveTable=" not in l:
                continue
            body = l.lstrip(f"{sign} ").rstrip()
            try:
                _, rest = body.split("=", 1)
            except ValueError:
                continue
            parts = rest.split(";", 4)
            if len(parts) < 5:
                continue
            path, action, identifier, input_val, new_val = parts
            if "." not in identifier:
                continue
            row, field = identifier.rsplit(".", 1)
            out.append((path, row, field, new_val, sign))
        return out

    async def send_embed_safe(self, channel, embed, file=None):
        embed.colour = None
        try:
            await channel.send(embed=embed, file=file)
            logging.info("Message sent successfully")
        except discord.HTTPException as he:
            msg = str(he).lower()
            if "embeds too large" in msg or "maximum number of embeds" in msg:
                fields = embed.fields
                chunks = [fields[i:i+5] for i in range(0, len(fields), 5)]
                for idx, chunk in enumerate(chunks, 1):
                    part = Embed(title=f"{embed.title} (part {idx}/{len(chunks)})", colour=None)
                    for f in chunk:
                        part.add_field(name=f.name, value=f.value, inline=f.inline)
                    try:
                        await channel.send(embed=part)
                        logging.info(f"Sent split embed part {idx}")
                    except Exception:
                        pass
        except Exception:
            pass

    async def poll_loop(self):
        await self.wait_until_ready()
        channel = self.get_channel(CHANNEL_ID)
        logging.info(f"Starting poll loop against {len(ENDPOINTS)} endpoints.")

        while True:
            logging.info("Fetching data from Cloud Storage endpoints…")
            for url in ENDPOINTS:
                key           = url.rsplit("/", 1)[-1]
                friendly_name = FILENAME_MAP.get(key, key)
                state_file    = os.path.join(STATE_DIR, f"{friendly_name}.json")

                # FETCH
                try:
                    text = await self.fetch_json(url)
                except Exception as e:
                    logging.info(f"[{friendly_name}] fetch error: {e} — skipping")
                    continue

                # DIFF LINES
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

                # overwrite state file
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(new_lines, f, indent=2)

                # parse raw diffs
                dt_plus       = self._parse_datatable(added, "+")
                dt_minus      = self._parse_datatable(removed, "-")
                ct_plus       = self._parse_curvetable(added, "+")
                ct_minus      = self._parse_curvetable(removed, "-")
                hotfixes_plus = self._parse_hotfix_strings(added)

                # prepare fallback diff JSON (but only send if no parsed mods)
                diff_payload = {"added": added, "removed": removed}
                diff_bytes   = json.dumps(diff_payload, indent=2).encode("utf-8")
                diff_file    = File(fp=io.BytesIO(diff_bytes), filename=f"{friendly_name}_diff.json")

                # ——— 1) DIFF SUMMARY EMBED ———
                total_parsed = (
                    len(dt_plus) + len(dt_minus) +
                    len(ct_plus) + len(ct_minus) +
                    len(hotfixes_plus)
                )

                if total_parsed == 0:
                    # fallback: send raw diff JSON only
                    await channel.send(file=diff_file)
                    logging.info(f"No parsed mods; raw diff for {friendly_name} sent.")
                else:
                    # DataTable embeds
                    dt_changes = dt_plus + dt_minus
                    if dt_changes:
                        by_path = {}
                        for path, row, field, val, sign in dt_changes:
                            by_path.setdefault(path, []).append((row, field, val, sign))
                        for path, mods in by_path.items():
                            e = Embed(title="Summary")
                            e.description = f"➥ **DataTable Modification:** ```{path}```"
                            for row, field, val, sign in mods:
                                e.add_field(
                                    name=f"`{row} → {field}`",
                                    value=f"{val}",
                                    inline=False
                                )
                            await self.send_embed_safe(channel, e)

                    # CurveTable embeds
                    ct_changes = ct_plus + ct_minus
                    if ct_changes:
                        by_path = {}
                        for path, row, field, val, sign in ct_changes:
                            by_path.setdefault(path, []).append((row, field, val, sign))
                        for path, mods in by_path.items():
                            e = Embed(title="Summary")
                            e.description = f"```{path}```"
                            for row, field, val, sign in mods:
                                e.add_field(
                                    name=f"{row}.{field}",
                                    value=f"{val}",
                                    inline=False
                                )
                            await self.send_embed_safe(channel, e)

                    # String embeds
                    if hotfixes_plus:
                        e = Embed(title="Summary")
                        e.description = "➥ **String modification detected**"
                        for key, text in hotfixes_plus:
                            e.add_field(
                                name=f"**{key}**",
                                value=f"➥ {text}",
                                inline=False
                            )
                        await self.send_embed_safe(channel, e)

                # ——— 2) PARSED JSON & COUNT EMBED ———
                section = {
                    "section_name": friendly_name,
                    "modifications": []
                }
                for k, t in hotfixes_plus:
                    section["modifications"].append({
                        "type":"String", "key":k, "value":t
                    })
                for path, row, field, val, s in dt_plus + dt_minus:
                    section["modifications"].append({
                        "type":"DataTable", "path":path,
                        "row_name":row, "field":field,
                        "new_value":val,
                        "change":"Added" if s=="+" else "Removed"
                    })
                for path, row, field, val, s in ct_plus + ct_minus:
                    section["modifications"].append({
                        "type":"CurveTable","path":path,
                        "row_name":row, "field":field,
                        "new_value":val,
                        "change":"Added" if s=="+" else "Removed"
                    })

                parsed_path = os.path.join(STATE_DIR, f"{friendly_name}_parsed.json")
                with open(parsed_path, "w", encoding="utf-8") as f:
                    json.dump([section], f, indent=4, ensure_ascii=False)

                count_embed = Embed(title=f"Parsed Updates in {friendly_name}")
                count_embed.add_field(name="Strings",     value=str(len(hotfixes_plus)), inline=True)
                count_embed.add_field(name="DataTables",  value=str(len(dt_plus)),         inline=True)
                count_embed.add_field(name="CurveTables", value=str(len(ct_plus)),         inline=True)
                total = (len(hotfixes_plus) + len(dt_plus) + len(dt_minus)
                         + len(ct_plus) + len(ct_minus))
                count_embed.add_field(name="Total Mods", value=str(total), inline=False)
                count_embed.set_footer(text=f"See attached {os.path.basename(parsed_path)} for details")

                with open(parsed_path, "rb") as fp:
                    parsed_file = File(fp, filename=os.path.basename(parsed_path))

                await self.send_embed_safe(channel, count_embed, file=parsed_file)

                # (Removed the third “String Hotfix Summary (EN only)” embed block here)

            logging.info(f"Waiting {POLL_INTERVAL}s before next poll")
            await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    bot = FortniteTrackerBot()
    bot.run(DISCORD_TOKEN)