import requests, json, sys
 
if len(sys.argv) != 2:
    print("Please specify a mixcloud account name to grab all Cloudcast links: mget.py keepingtheravealive")
    sys.exit()
   
r = requests.get("https://api.mixcloud.com/" + sys.argv[1] + "/cloudcasts/")
json_r = json.loads(r.text)
full_list = []
 
if 'data' not in json_r:
    print("The username was not found or the user does not have any 'shows' on their profile")
    sys.exit()
 
while True:
    for i in range(0, len(json_r["data"])):
        full_list.append("https://mixcloud.com"+json_r["data"][i]["key"])
    if 'next' not in json_r["paging"]: break
    r = requests.get(json_r["paging"]["next"])
    json_r = json.loads(r.text)
   
with open('mc_list_'+sys.argv[1], 'w') as f:
    for item in full_list:
        f.write("%s\n" % item)
       
print("Found "+str(len(full_list)) + " links for user \""+sys.argv[1]+"\". All links are in the file mc_list_"+sys.argv[1])
print("Use this list with youtube-dl and the parameter -a mc_list_"+sys.argv[1])
