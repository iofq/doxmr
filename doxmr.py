import datetime
import json
import sys
import os
import requests
import subprocess

key = sys.argv[1]
api_endpoint="https://api.digitalocean.com/v2/"
api_headers={
    "Content-Type":"application/json", 
    "Authorization":"Bearer " + key
}

def main() :

    if len(key) != 64: 
        print("invalid api key")
        sys.exit(1)

    #Read ssh key from config/id_rsa.pub
    ssh_key_file = open("config/id_rsa.pub", "r")
    ssh_key = ssh_key_file.read()

    #Check if key is duplicate and append to keystore
    with open("config/keys", "a+") as api_key_file:
        for k in api_key_file:
            if key == k.rstrip():
                print("duplicate key")
                return 1
        api_key_file.write(key)

    create_ssh_key(ssh_key)
    apply_terraform(key)
    build_inventory()
    apply_ansible()

def get_ips():
    ips = []
    r = requests.get(api_endpoint + "droplets", headers=api_headers)
    for a in json.loads(r.text)['droplets']:
        network = a['networks']['v4']
        for i,_ in enumerate(network):
            if str(network[i]['type']) == 'public':
                ips.append(str(network[i]['ip_address']))
    return ips

def get_active_droplets():
    r = requests.get(api_endpoint + "droplets", headers=api_headers)
    droplets = []
    for d in json.loads(r.text)['droplets']:
        droplets.append(str(d['id']))
    return droplets

def get_creation_date():
    r = requests.get(api_endpoint + "actions", headers=api_headers)
    droplets =  get_active_droplets(api_headers)
    for a in json.loads(r.text)['actions']:
        if str(a['type']) == 'create' and str(a['resource_id']) in droplets:
            date = datetime.datetime.strptime(str(a['completed_at']), "%Y-%m-%dT%H:%M:%SZ")
            print(str(a['completed_at']), str(date.utcnow() - date))

def create_ssh_key(ssh_key):
    r = requests.post(api_endpoint + "account/keys", headers=api_headers, data=json.dumps({ "name":"key","public_key": ssh_key}))
    try:
        print("ssh fingerprint: ", str(json.loads(r.text)['ssh_key']['fingerprint']))
    except:
        print("ssh key (probably) already exists")

def apply_terraform(key):
    cwd = os.getcwd()
    os.chdir("terraform/")
    output = subprocess.run(["terraform", "init"])
    output = subprocess.run(["terraform", "workspace", "new", key])
    output = subprocess.run(["terraform", "apply", "-var=do_api_token=" + key])
    os.chdir(cwd)

def build_inventory():
    with open("ansible/inventory", "a+") as inventory:
        ips = [line.strip() for line in inventory.readlines()]
        if (ips == []) or (ips[0] != '[compute]'):
            inventory.write("[compute]\n")
        for i in get_ips():
            if i not in ips:
                inventory.write(i + "\n")

def apply_ansible():
    cwd = os.getcwd()
    os.chdir("ansible/")
    output = subprocess.run(["ansible-playbook", "-i", "inventory", "site.yml"])
    os.chdir(cwd)

if __name__ == "__main__":
    main()
