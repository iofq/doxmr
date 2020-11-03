import base64
import datetime
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
import time
import requests

DATABASE_LOCATION = "data/store.db"
SSH_KEY_LOCATION = "data/id_rsa.pub"
os.environ["TF_IN_AUTOMATION"] = "true"

try:
    db = sqlite3.connect(DATABASE_LOCATION)
    cursor = db.cursor()
except sqlite3.Error:
    print("Error accessing sqlite3 database ", DATABASE_LOCATION)
    sys.exit(1)
try:
    ssh_key = open(SSH_KEY_LOCATION, "r").read()
except FileNotFoundError:
    print("Error accessing ssh key ", SSH_KEY_LOCATION)

def print_red(string):
    print("\033[91m {}\033[00m".format(string), end="")
def print_green(string):
    print("\033[92m {}\033[00m".format(string), end="")
def print_yellow(string):
    print("\033[93m {}\033[00m".format(string), end="")
def print_light_purple(string):
    print("\033[94m {}\033[00m".format(string), end="")
def print_purple(string):
    print("\033[95m {}\033[00m".format(string), end="")
def print_cyan(string):
    print("\033[96m {}\033[00m".format(string), end="")
def print_light_gray(string):
    print("\033[97m {}\033[00m".format(string), end="")
def print_black(string):
    print("\033[98m {}\033[00m".format(string), end="")

def usage():
    print_light_purple("\n doxmr: create and provision droplets on DigitalOcean\n")
    print("-------------------------------------\n")
    print_green("doxmr add <api_key> <api_key>...\n")
    print(" --  append key(s) to database, provision droplets according to config")
    print(" --  in terraform/do.tf and ansible/site.yml.\n")
    print_purple("doxmr ls\n")
    print(" -- prints a formatted list of stored keys and droplets\n")
    print_purple("doxmr refresh <api_key>...\n")
    print(" -- reruns terraform and ansible on all keys (or <api_keys>)\n")
    print_red("doxmr prune\n")
    print(" -- find, remove expired & unreachable keys/droplets from database. ")
    print(" -- be careful, lost keys are a pain to recover. \n")

def main():

    r = requests.get("https://s2k7tnzlhrpw.statuspage.io/api/v2/components.json")
    body = json.loads(r.text)
    for b in body["components"]:
        if b["name"] == "API":
            print_yellow("DigitalOcean API status: {}\n".format(b["status"]))

    try:
        command = sys.argv[1]
    except IndexError:
        command = "usage"

    init_db()
    if command == "add":
        keys = sys.argv[2:]
        if not keys:
            usage()
        else:
            accounts = []
            for k in keys:
                if not len(k) == 64:
                    print("invalid key: ", k)
                    continue
                a = DOAccount(api_key=k, ssh_key=ssh_key)
                if store_key(a):
                    print("ignoring duplicate key")
                else:
                    accounts.append(a)
            provision(accounts)
    elif command == "ls":
        ls()
    elif command == "refresh":
        keys = sys.argv[2:]
        if not keys:
            usage()
        else:
            if keys[0] == "all":
                cursor.execute("""
                    SELECT key FROM keys;
                """)
                accounts = []
                for k in cursor.fetchall():
                    accounts.append(DOAccount(api_key=k[0], ssh_key=ssh_key))
                provision(accounts)

            else:
                accounts = []
                for k in keys:
                    if not len(k) == 64:
                        print("invalid key: ", k)
                        sys.exit(1)
                    accounts.append(DOAccount(api_key=k[0], ssh_key=ssh_key))
                provision(accounts)
    elif command == "prune":
        prune()
    elif command == "shutdown":
        shutdown()
    else:
        usage()

    db.commit()
    db.close()

def init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys(key_id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL)
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS droplets(key_id INTEGER NOT NULL, id TEXT, ipv4 TEXT, date TEXT, ttl INTEGER)
    """)
    db.commit()

def store_droplets(account):
    droplets = account.get_active_droplets()
    for d in droplets:
        cursor.execute("""
            SELECT * FROM droplets WHERE id=?""", (d["id"],))
        if not cursor.fetchall():
            cursor.execute("""
                INSERT INTO droplets(key_id, id, ipv4, date, ttl) VALUES((SELECT key_id FROM keys WHERE key=?),?,?,?, ?)""", (account.api_key, d["id"], d["ipv4"], d["date"], account.ttl))
            db.commit()

def store_key(account):
    cursor.execute("""
        SELECT * FROM keys WHERE key=?""", (account.api_key,))
    if not cursor.fetchall():
        cursor.execute("""
          INSERT INTO keys(key) VALUES(?)""", (account.api_key,))
        db.commit()
        return 0
    else:
        return 1

def provision(accounts):
    for a in accounts:
        a.create_ssh_key()
        apply_terraform(a)
    if a != []:
        print("Waiting for Droplets...")
        time.sleep(15)
    build_inventory(accounts)
    apply_ansible()
    for a in accounts:
        store_droplets(a)
    os.remove("ansible/inventory")

def apply_terraform(account):
    cwd = os.getcwd()
    os.chdir("terraform/")
    subprocess.run(["terraform", "init"], check=True)
    subprocess.run(["terraform", "workspace", "new", account.api_key], check=False)
    subprocess.run(["terraform", "workspace", "select", account.api_key], check=True)
    subprocess.run(["terraform", "apply", "-auto-approve", "-var=do_api_token=" + account.api_key, "-var=do_ssh_key=" + account.ssh_key_fingerprint], check=True)
    output = subprocess.run(["terraform", "output"], encoding='utf-8', stdout=subprocess.PIPE, check=True)
    ttl = output.stdout.split('\n')[0].split(" ")[2]
    account.ttl = math.floor(float(ttl))
    os.chdir(cwd)

def build_inventory(accounts):
    with open("ansible/inventory", "w+") as inventory:
        inventory.write("[compute]\n")
        for a in accounts:
            for d in a.get_active_droplets():
                inventory.write(d["ipv4"] + " api_key=" + a.api_key + " ttl=" + str(a.ttl) + " date=" + d["date"] + "\n" )

def apply_ansible():
    cwd = os.getcwd()
    os.chdir("ansible/")
    subprocess.run(["ansible-playbook", "-i", "inventory", "site.yml"], check=False)
    os.chdir(cwd)

def ls():
    cursor.execute("""
        SELECT key FROM keys;
    """)
    for i in cursor.fetchall():
        cursor.execute("""
            SELECT * FROM droplets WHERE key_id=(SELECT key_id FROM keys WHERE key=?);""", (i[0],))
        status = DOAccount(api_key=i[0]).get_status()
        balance = DOAccount(api_key=i[0]).get_balance()
        print_green("email: {}  status: {}  ratelimit: {} balance: {}\n".format(status[0], status[1], status[2], balance))
        print_purple(i[0] + "\n")
        for d in cursor.fetchall():
            time_left = math.floor((math.floor(float(d[3])) + int(d[4]) * 3600) - time.time()) / 3600
            print_cyan("    id=")
            print(d[1], end="")
            print_cyan("    ipv4=")
            print(d[2].ljust(16, " "), end="")
            print("     with\033[96m {}\033[00m hours left.".format(int(time_left)))
        print()

def prune():
    print_green("Looking for expired resources...\n")
    cursor.execute("""
        SELECT key from keys;
    """)
    accounts = []
    active_droplets = []
    for k in cursor.fetchall():
        droplets = DOAccount(api_key=k[0]).get_active_droplets()
        if droplets == []:
            accounts.append(k[0])
        else:
            for d in droplets:
                active_droplets.append(int(d["id"]))

    cursor.execute("""
        SELECT id,ipv4,date,ttl,key_id FROM droplets;
    """)
    expired = []
    unreachable = []
    for d in cursor.fetchall():
        if time.time() > (math.floor(float(d[3])) + (math.floor(float(d[2])) * 3600)):
            expired.append((d[0], d[1]))
        elif int(d[0]) not in active_droplets:
            cursor.execute("""
                SELECT key FROM keys WHERE key_id=?""",(d[4],))
            key =  cursor.fetchone()
            try:
                if DOAccount(api_key=key[0]).get_droplet(d[0])["id"] == "not_found":
                    unreachable.append((d[0], d[1]))
            except KeyError as e:
                continue

    if expired != []:
        print_red("Pruning these expired droplets:\n")
        for e in expired:
            print("\t{}, {}".format(e[0], e[1]))
    if unreachable != []:
        print_red("Pruning these unreachable droplets:\n")
        for u in unreachable:
            print("\t{}, {}".format(u[0], u[1]))
    if accounts != []:
        print_red("Pruning these empty accounts:\n")
        for a in accounts:
            print("\t{}".format(a))
    if not expired == unreachable == accounts == []:
        print_green("Does this look correct?")
        print_green("\n (Only 'yes' will be accepted as confirmation): ")
        answer = input("")
        if answer == "yes":
            for e in expired + unreachable:
                cursor.execute("""
                    DELETE FROM droplets WHERE id=?""", (e[0],))
            for a in accounts:
                cursor.execute("""
                    DELETE FROM keys WHERE key=?""", (a,))
                subprocess.run(["terraform", "workspace", "delete", a], check=False)
            print_green("Done.\n")
    else:
        print_red("Nothing found to prune.\n")
    db.commit()

def shutdown():
    print_red("Destroy all droplets for all keys???\n")
    print_red("(Only 'yes' will be accepted as confirmation): ")
    answer = input("")
    if answer == "yes":
        cursor.execute("""
            SELECT key FROM keys;
        """)
        keys = cursor.fetchall()
        for k in keys:
            api_headers={
                "Content-Type":"application/json",
                "Authorization":"Bearer " + k[0]
            }
            status_code = 0
            while status_code != 204:
                r = requests.delete(DOAccount("").api_endpoint + "droplets" + "?tag_name=doxmr", headers=api_headers)
                status_code = r.status_code
                if status_code == 204:
                    print_red("Account shutdown: {}\n".format(k[0]))

class DOAccount:

    def __init__(self, api_key, ssh_key="", ttl=1):
        self.api_endpoint="https://api.digitalocean.com/v2/"
        self.api_key = api_key
        self.ssh_key = ssh_key
        if self.ssh_key != "":
            self.ssh_key_fingerprint = self.md5_fingerprint(self.ssh_key)
        self.ttl = ttl
        self.api_headers={
            "Content-Type":"application/json",
            "Authorization":"Bearer " + self.api_key
        }

    @staticmethod
    def md5_fingerprint(key):
        key = base64.b64decode(key.strip().split()[1].encode('ascii'))
        fp_plain = hashlib.md5(key).hexdigest()
        return ':'.join(a+b for a,b in zip(fp_plain[::2], fp_plain[1::2]))

    def create_ssh_key(self):
        r = requests.post(self.api_endpoint + "account/keys", headers=self.api_headers, data=json.dumps({ "name": self.api_key[:3],"public_key": self.ssh_key}))
        try:
            fingerprint = str(json.loads(r.text)['ssh_key']['fingerprint'])
            print_green("ssh fingerprint: {}\n".format(fingerprint))
        except KeyError:
            print_red("ssh key already exists!\n")

    def get_droplet(self, droplet_id):
        status_code = 0
        while status_code not in [200,404]:
            r = requests.get(self.api_endpoint + "droplets/" + str(droplet_id), headers=self.api_headers)
            status_code = r.status_code
        return json.loads(r.text)

    def get_ip(self, droplet_id):
        network = self.get_droplet(droplet_id)['droplet']['networks']['v4']
        for i,_ in enumerate(network):
            if str(network[i]['type']) == 'public':
                return str(network[i]['ip_address'])

    #return [email, status, ratelimit]
    def get_status(self):
        status_code = 0
        while status_code != 200:
            r = requests.get(self.api_endpoint + "account/", headers=self.api_headers)
            status_code = r.status_code
        body = json.loads(r.text)["account"]
        return [body["email"], body["status"], r.headers["Ratelimit-Remaining"]]

    def get_balance(self):
        status_code = 0
        while status_code != 200:
            r = requests.get(self.api_endpoint + "customers/my/balance", headers=self.api_headers)
            status_code = r.status_code
        body = json.loads(r.text)
        return abs(float(body["month_to_date_balance"]))

    #return {"id": id, "ipv4": 0.0.0.0, "date": unix_time}
    def get_active_droplets(self):
        status_code = 0
        while status_code != 200:
            r = requests.get(self.api_endpoint + "droplets", headers=self.api_headers)
            status_code = r.status_code
        droplets = []
        for d in json.loads(r.text)['droplets']:
            date =  str(int(datetime.datetime.strptime(str(d['created_at']), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()))
            droplets.append({"id": d['id'], "ipv4": self.get_ip(d['id']), "date": date})
        return droplets

if __name__ == "__main__":
    main()
