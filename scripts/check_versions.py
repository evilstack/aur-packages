# SPDX-FileCopyrightText: 2026 evilstack
#
# SPDX-License-Identifier: MIT

import os
import requests
from packaging.version import Version

# Define the packages you maintain
PACKAGES = [
    {
        "name": "pan-python",
        "github": "kevinsteves/pan-python",
        "pypi": "pan-python",
        "aur": "python-pan-python",
    },
    {
        "name": "pan-os-python",
        "github": "PaloAltoNetworks/pan-os-python",
        "pypi": "pan-os-python",
        "aur": "python-pan-os-python",
    },
    {
        "name": "pan-os-upgrade-assurance",
        "github": "PaloAltoNetworks/pan-os-upgrade-assurance",
        "pypi": "panos-upgrade-assurance",
        "aur": "python-pan-os-upgrade-assurance",
    },
    {
        "name": "pan-chainguard",
        "github": "PaloAltoNetworks/pan-chainguard",
        "pypi": "pan-chainguard",
        "aur": "pan-chainguard",
    },
]

NTFY_TOPIC = os.environ.get("NTFY_TOPIC")
NTFY_URL = os.environ.get("NTFY_URL")

def get_github_version(repo):
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json().get("tag_name", "").lstrip("v")
    # Fallback to tags if no official release object exists
    url_tags = f"https://api.github.com/repos/{repo}/tags"
    r_tags = requests.get(url_tags)
    if r_tags.status_code == 200 and r_tags.json():
        return r_tags.json()[0].get("name", "").lstrip("v")
    return "Unknown"

def get_pypi_version(pypi_name):
    url = f"https://pypi.org/pypi/{pypi_name}/json"
    r = requests.get(url)
    if r.status_code == 200:
        return r.json().get("info", {}).get("version", "Unknown")
    return "Unknown"

def get_aur_version(aur_name):
    url = f"https://aur.archlinux.org/rpc/v5/info?arg[]={aur_name}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        results = data.get("results", [])
        if results:
            # Strip PKGBUILD release suffix if present (e.g., -1)
            full_ver = results[0].get("Version", "Unknown")
            return full_ver.split("-")[0]
    return "Unknown"

def send_notification(message):
    if NTFY_TOPIC:
        requests.post(f"https://{NTFY_URL}/{NTFY_TOPIC}", data=message.encode("utf-8"), headers={"Title": "AUR Maintainer Alert"})

def main():
    table_rows = []
    alerts = []

    for pkg in PACKAGES:
        gh_ver = get_github_version(pkg["github"])
        pypi_ver = get_pypi_version(pkg["pypi"])
        aur_ver = get_aur_version(pkg["aur"])

        # Determine status relative to your GitHub source
        status = "🟢 Up to Date"
        try:
            if gh_ver != "Unknown" and aur_ver != "Unknown" and Version(gh_ver) > Version(aur_ver):
                status = "🟠 AUR Update Needed"
                alerts.append(f"{pkg['aur']} is behind GitHub ({gh_ver} vs AUR {aur_ver})")
            if gh_ver != "Unknown" and pypi_ver != "Unknown" and Version(gh_ver) > Version(pypi_ver):
                status += " (PyPI Behind)"
        except Exception:
            pass

        row = f"| `{pkg['name']}` | `{gh_ver}` | `{pypi_ver}` | `{aur_ver}` | {status} |"
        table_rows.append(row)

    # Read existing README and replace table contents between markers
    readme_path = "README.md"
    if os.path.exists(readme_path):
        with open(readme_path, "r") as f:
            content = f.read()

        new_table = "\n".join([
            "| Package | GitHub (Source) | PyPI | AUR | Status |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ] + table_rows)

        start_marker = "<!-- BEGIN_PACKAGE_TABLE -->"
        end_marker = "<!-- END_PACKAGE_TABLE -->"

        if start_marker in content and end_marker in content:
            pre = content.split(start_marker)[0]
            post = content.split(end_marker)[1]
            updated_content = f"{pre}{start_marker}\n{new_table}\n{end_marker}{post}"

            with open(readme_path, "w") as f:
                f.write(updated_content)

    if alerts and NTFY_TOPIC:
        send_notification("\n".join(alerts))

if __name__ == "__main__":
    main()
