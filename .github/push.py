import requests
from datetime import datetime
import os
import sys
import json
from io import BytesIO
from urllib.parse import urlparse

file_path = sys.argv[1]

telegram_to = os.environ["TELEGRAM_TO"]
telegram_token = os.environ["TELEGRAM_TOKEN"]

def get_commit_hash(branch, codename):
    path = f"changelogs/{codename}.txt"
    api_url = f"https://api.github.com/repos/0xSoul24/OTA/commits?path={path}&sha={branch}"
    response = requests.get(api_url)
    response.raise_for_status()
    commits = response.json()
    if commits:
        return commits[0]['sha']
    else:
        return "Unknown"

def parse_device():
    with open(file_path) as f:
        codename = f.name.split("/")[-1].split(".")[0]
        data = json.load(f)
        response = data["response"]
        filename = response[0]["filename"]
        oem = response[0]["oem"]
        device = response[0]["device"]
        maintainer = response[0]["maintainer"]
        version = response[0]["version"]
        build_date = response[0]["timestamp"]
        file_size = response[0]["size"]
        download_link = response[0]["download"]
        xda_thread = response[0]["forum"]
        github = response[0]["github"]
        md5 = response[0]["md5"]
        sha256 = response[0]["sha256"]
        initial_installation_images = response[0]["initial_installation_images"]
    return filename, codename, oem, device, maintainer, version, build_date, file_size, download_link, xda_thread, github, md5, sha256, initial_installation_images

def humanize(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"

def telegram_send():
    filename, codename, oem, device, maintainer, version, build_date, file_size, download_link, xda_thread, github, md5, sha256, initial_installation_images = parse_device()
    
    # Extract only the branch name from GITHUB_REF, default to 'bka'
    branch = os.environ.get("GITHUB_REF", "refs/heads/bka").split("/")[-1]
    commit_hash = get_commit_hash(branch, codename)

    has_xda_thread = xda_thread and xda_thread != "null" and xda_thread.strip() != ""
    
    message = f"""
<b>New build available!</b>
\U0001f4f2 \u2022 New build available for <b>{oem} {device}</b> ({codename})
\U0001f464 \u2022 <b>By <a href="https://github.com/{github}">{maintainer}</a></b>

\U0001f4e6 \u2022 <b>Version:</b> {version}
\U0001f552 \u2022 <b>Build date:</b> {datetime.fromtimestamp(build_date).date()}
\U0001f4ce \u2022 <b>Build size:</b> {humanize(file_size)}
\U0001f517 \u2022 <b>MD5:</b> <code>{md5}</code>
\U0001f517 \u2022 <b>SHA256:</b> <code>{sha256}</code>
    """

    parsed = urlparse(download_link)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Base inline keyboard buttons
    inline_keyboard = [
        [
            {"text": "\U0001f5de\ufe0f Changelog \U0001f5de\ufe0f", "url": f"https://raw.githubusercontent.com/0xSoul24/OTA/{commit_hash}/changelogs/{codename}.txt"},
            {"text": "\u2b07\ufe0f ROM \u2b07\ufe0f", "url": download_link}
        ],
        [
            {"text": "\u262f KernelSU-Next \u262f", "url": f"{base_url}/KernelSU-Next.img"},
            {"text": "\U0001F977 KernelSU-Next-SUSFS \U0001F977", "url": f"{base_url}/KernelSU-Next-SUSFS.img"}
        ],
        [
            {"text": "\U0001f310 XDA Thread \U0001f310", "url": xda_thread}
        ]
    ]

    # Dynamically generate buttons for each initial installation image
    image_buttons = []
    for image in initial_installation_images:
        img_url = f"{base_url}/{image}.img"
        image_buttons.append({"text": f"\u2b07\ufe0f {image} \u2b07\ufe0f", "url": img_url})
    
    # Insert image buttons as a new row in the keyboard
    inline_keyboard.insert(1, image_buttons)
    
    inline_keyboard_structure = {"inline_keyboard": inline_keyboard}

    image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS7DK6a--HvqADA_u3mGjXSVUvxxZ5sw3x9Sw&s"
    image_response = requests.get(image_url)
    if (image_response.status_code == 200):
        image_file = BytesIO(image_response.content)
        image_file.name = "keepevolving.png"
        photo_url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
        payload = {
            "chat_id": telegram_to,
            "caption": message,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(inline_keyboard_structure)
        }
        files = {"photo": image_file}
        result = requests.post(photo_url, data=payload, files=files)
        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print("Failed to send photo message:", err)
        else:
            print("Photo message delivered successfully, code {}.".format(result.status_code))
    else:
        print("Failed to download the image.")

telegram_send()