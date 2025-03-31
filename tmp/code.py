import subprocess
import requests

# Install required libraries
subprocess.run(['pip', 'install', 'requests', 'pyyaml'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# GitHub Action YAML content
github_action = """
name: CI

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2

      - name: tanmay.mehrotra@gramener.com
        run: echo "Hello, world!"
"""

# GitHub API details
url = 'https://api.github.com/repos/ta1789/TDSProject_Test/actions/workflows'
token = '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'
headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}

# Create the GitHub Action workflow
response = requests.post(url, headers=headers, json={"name": "CI", "path": ".github/workflows/ci.yml", "content": github_action})

# Print the response
print(response.json())