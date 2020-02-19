import json, sys

import requests


if len(sys.argv) != 2:
    print("Please specify a mixcloud account name to grab all Cloudcast links: "
          "mget.py keepingtheravealive")
    sys.exit()

artist_name = sys.argv[1]

r = requests.get(f'https://api.mixcloud.com/{artist_name}/cloudcasts/')
json_r = json.loads(r.text)
full_list = []

if 'data' not in json_r:
    print("The username was not found or the user does not have any 'shows' on their profile")
    sys.exit()

data = json_r['data']

while True:
    for i in range(0, len(data)):
        full_list.append(f"https://mixcloud.com{data[i]['key']}")
    if 'next' not in json_r['paging']:
        break
    r = requests.get(json_r['paging']['next'])
    json_r = json.loads(r.text)

with open(f'mc_list_{artist_name}', 'w') as f:
    for item in full_list:
        f.write(f'{item}\n')

print(f'Found {str(len(full_list))} links for user "{artist_name}". '
      f'All links are in the file mc_list_{artist_name}')
print(f"Use this list with youtube-dl and the parameter -a mc_list_{artist_name}")
