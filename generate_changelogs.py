import requests
import boto3
from bs4 import BeautifulSoup
from datetime import datetime
import os
import re

# List your repos (update with yours)
repos = [
    'oreliousw/pine-scripts',
    'oreliousw/aws-oanda',
    'oreliousw/aws-testing',
    # Add more: 'username/repo'
]

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
headers = {'Authorization': f'token {GITHUB_TOKEN}'} if GITHUB_TOKEN else {}

s3 = boto3.client('s3', aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'), region_name='us-east-1')
bucket = os.getenv('S3_BUCKET')

def fetch_changelog(repo):
    url = f"https://raw.githubusercontent.com/{repo}/main/CHANGELOG.md"
    response = requests.get(url, headers=headers)
    return response.text if response.status_code == 200 else None

def parse_changelog(content):
    if not content:
        return []
    sections = re.split(r'^##\s+\[([^\]]+)\]', content, flags=re.MULTILINE)
    entries = []
    for i in range(1, len(sections), 2):
        if i + 1 >= len(sections):
            break
        version = sections[i].strip()
        body = sections[i + 1].strip()
        lines = body.splitlines()
        date = 'N/A'
        changes_body = body
        if lines:
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', lines[0])
            if date_match:
                date = date_match.group()
                changes_body = '\n'.join(lines[1:]).strip()
        changes = re.sub(r'^\s*-?\s*', '', changes_body, flags=re.MULTILINE).strip()[:200] + '...'
        entries.append({'version': version, 'date': date, 'changes': changes})
    return entries[:3]  # First 3 versions (newest, assuming CHANGELOG has newest first)

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>O169 Changelog Hub</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f4f4; color: #333; margin: 20px; }
        h1 { color: #EE7C6B; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background: #EE7C6B; color: white; }
        .repo { font-weight: bold; color: #EE7C6B; }
        .version { font-size: 1.1em; }
        input[type="text"] { width: 100%; padding: 10px; margin-bottom: 10px; }
    </style>
</head>
<body>
    <h1>Orelius Changelog Hub (o169.com)</h1>
    <p>Last updated: {}</p>
    <input type="text" id="search" placeholder="Search changelogs...">
    <table id="changelogTable">
        <thead><tr><th>Repo</th><th>Version</th><th>Date</th><th>Changes</th></tr></thead>
        <tbody>
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

tbody_rows = ""
for repo in repos:
    content = fetch_changelog(repo)
    entries = parse_changelog(content)
    for entry in entries:
        tbody_rows += f"""
        <tr>
            <td class="repo">{repo}</td>
            <td class="version">{entry['version']}</td>
            <td>{entry['date']}</td>
            <td>{entry['changes']}</td>
        </tr>
        """

html_content = html_template + tbody_rows + """
        </tbody>
    </table>
    <script>
        document.getElementById('search').addEventListener('input', (e) => {
            const rows = document.querySelectorAll('#changelogTable tbody tr');
            rows.forEach(row => {
                row.style.display = row.textContent.toLowerCase().includes(e.target.value.toLowerCase()) ? '' : 'none';
            });
        });
    </script>
</body>
</html>
"""

# Write index.html
with open('index.html', 'w') as f:
    f.write(html_content)

# FIXED: Remove 'ACL' to avoid AccessControlListNotSupported error for buckets that don't support ACLs
# Ensure your S3 bucket policy allows public reads if needed
s3.upload_file('index.html', bucket, 'index.html', ExtraArgs={'ContentType': 'text/html'})
print(f"Synced to s3://{bucket}/index.html")
