import datetime
import json
import math
import os
import requests
import sqlite3
import subprocess
import sys
import time

database_location = 'config/store.db'
try:
    db = sqlite3.connect(database_location)
    cursor = db.cursor()
except sqlite3.Error as e:
    print("Error connecting to sqlite3 database ", database_location)

def init():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys(key_id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS droplets(key_id INTEGER NOT NULL, id TEXT, ipv4 TEXT, date TEXT)
    """)
    db.commit()

def main():

    #TODO: args and flags

    key = sys.argv[1]
    if len(key) != 64: 
        print("invalid api key")
        sys.exit(1)

    #Read ssh key from config/id_rsa.pub
    ssh_key = open("config/id_rsa.pub", "r").read()

    account =  DOAccount(api_key=key, ssh_key=ssh_key)
    if not store_key(account):
        print("ignoring duplicate key")

    provision(account)
    store_droplets(account)
        
def provision(account):
    account.create_ssh_key()
    apply_terraform(account) 
    print("Waiting for Droplets...")
    time.sleep(15)
    build_inventory(account)
    apply_ansible()

def store_droplets(account):
    droplets = account.get_active_droplets()
    for d in droplets:
        cursor.execute("""
            SELECT * FROM droplets WHERE id=?""", (d["id"],))
        if cursor.fetchall():
            return 1 
        else:
            cursor.execute("""
                INSERT INTO droplets(key_id, id, ipv4, date) VALUES((SELECT key_id FROM keys WHERE key=?),?,?,?)""", (account.api_key, d["id"], d["ipv4"], d["date"]))
            db.commit()

def store_key(account):
    cursor.execute("""
        SELECT * FROM keys WHERE key=?""", (account.api_key,))
    if cursor.fetchall():
        return 1 
    else:
        cursor.execute("""
            INSERT INTO keys(key) VALUES(?)""", (account.api_key,))
        db.commit()

def refresh_accounts(accounts):
    for a in accounts:
       a.create_ssh_key()
       apply_terraform(a) 
    print("Waiting for Droplets...")
    time.sleep(15)
    for a in accounts:
        build_inventory(a)
    apply_ansible()

def apply_terraform(account):
    cwd = os.getcwd()
    os.chdir("terraform/")
    output = subprocess.run(["terraform", "init"])
    output = subprocess.run(["terraform", "workspace", "new", account.api_key])
    output = subprocess.run(["terraform", "workspace", "select", account.api_key])
    output = subprocess.run(["terraform", "apply", "-var=do_api_token=" + account.api_key])
    output = subprocess.run(["terraform", "output"], encoding='utf-8', stdout=subprocess.PIPE)
    ttl = output.stdout.split('\n')[0].split(" ")[2]
    account.ttl = math.floor(float(ttl))
    os.chdir(cwd)

def build_inventory(account):
    with open("ansible/inventory", "a+") as inventory:
        inventory.seek(0)
        hosts = [line.strip() for line in inventory.readlines()]
        if (hosts == []) or (hosts[0] != '[compute]'):
            inventory.write("[compute]\n")
        for d in account.get_active_droplets():
            if d["ipv4"] not in hosts:
                inventory.write(d["ipv4"] + " api_key=" + account.api_key + " ttl=" + str(account.ttl) + "\n" )

#Apply ansible on entire dynamically built inventory
def apply_ansible():
    cwd = os.getcwd()
    os.chdir("ansible/")
    output = subprocess.run(["ansible-playbook", "-i", "inventory", "site.yml"])
    os.chdir(cwd)

class DOAccount:

    def __init__(self, api_key, ssh_key):
        self.api_endpoint="https://api.digitalocean.com/v2/"
        self.api_key = api_key
        self.ssh_key = ssh_key
        self.ttl = 1
        self.api_headers={
            "Content-Type":"application/json", 
            "Authorization":"Bearer " + self.api_key
        }

    def create_ssh_key(self):
        r = requests.post(self.api_endpoint + "account/keys", headers=self.api_headers, data=json.dumps({ "name":"key","public_key": self.ssh_key}))
        try:
            print("ssh fingerprint: ", str(json.loads(r.text)['ssh_key']['fingerprint']))
        except:
            print("ssh key (probably) already exists")

    def get_ip(self, id):
        ips = []
        r = requests.get(self.api_endpoint + "droplets/" + str(id), headers=self.api_headers)
        network = json.loads(r.text)['droplet']['networks']['v4']
        for i,_ in enumerate(network):
            if str(network[i]['type']) == 'public':
                return str(network[i]['ip_address'])

    def get_active_droplets(self):
        r = requests.get(self.api_endpoint + "droplets", headers=self.api_headers)
        droplets = []
        for d in json.loads(r.text)['droplets']:
            droplets.append({"id": d['id'], "ipv4": self.get_ip(d['id']), "date": str(datetime.datetime.strptime(str(d['created_at']), "%Y-%m-%dT%H:%M:%SZ"))})
        return droplets

    def to_json(self):
        return { self.api_key: self.get_active_droplets() }
                        

if __name__ == "__main__":
    d = DOAccount(api_key="55018d84fa5015c411534c95d0061919a66364b8104c9b71bd5b0ea0989682e8", ssh_key=open("config/id_rsa.pub","r").read())
    e = DOAccount(api_key="391afd0631a0d9fa2ca2ee2b47db1f3114d421b750f60244a07c11f07167dadf", ssh_key=open("config/id_rsa.pub","r").read())
    # init()
    # store_key(d) 
    # store_key(e) 
    # apply_terraform(d)
    # apply_terraform(e)
    # time.sleep(10)
    print(d.get_active_droplets())
    print(e.get_active_droplets())
    # build_inventory(d)
    # build_inventory(e)

    # store_droplets(d)
    # store_droplets(e)

    db.close()
