import base64
import datetime
import hashlib
import json
import math
import os
import requests
import sqlite3
import subprocess
import sys
import time

database_location = "config/store.db"
ssh_key_location = "config/id_rsa.pub"
os.environ["TF_IN_AUTOMATION"] = "true"

try:
    db = sqlite3.connect(database_location)
    cursor = db.cursor()
except sqlite3.Error as e:
    print("Error accessing sqlite3 database ", database_location)
    sys.exit(1)
try:
    ssh_key = open("config/id_rsa.pub", "r").read()
except:
    print("Error accessing ssh key ", ssh_key_location)

def printRed(string): print("\033[91m {}\033[00m".format(string), end="") 
def printGreen(string): print("\033[92m {}\033[00m".format(string), end="") 
def printYellow(string): print("\033[93m {}\033[00m".format(string), end="") 
def printLightPurple(string): print("\033[94m {}\033[00m".format(string), end="") 
def printPurple(string): print("\033[95m {}\033[00m".format(string), end="") 
def printCyan(string): print("\033[96m {}\033[00m".format(string), end="") 
def printLightGray(string): print("\033[97m {}\033[00m".format(string), end="") 
def printBlack(string): print("\033[98m {}\033[00m".format(string), end="") 

def help():
    printLightPurple("\n doxmr: create and provision droplets on DigitalOcean\n")
    print("-------------------------------------\n")
    printGreen("doxmr init\n")
    print(" -- creates management Docker container, mounts the current directory\n")
    printGreen("doxmr add <api_key> <api_key>...\n")
    print(" --  append key(s) to database, provision droplets according to config")
    print(" --  in terraform/do.tf and ansible/site.yml.\n")
    printPurple("doxmr ls\n")
    print(" -- prints a formatted list of stored keys and droplets\n")
    printPurple("doxmr refresh <api_key>...\n")
    print(" -- reruns terraform and ansible on all keys (or <api_keys>)\n")
    printRed("doxmr purge\n")
    print(" -- find, remove expired & unreachable keys/droplets from database. ")
    print(" -- be careful, lost keys are a pain to recover. \n")

def main():

    init_db()
    try:
        command = sys.argv[1]
    except IndexError as e:
        command = "help"

    if command == "add":
        keys = sys.argv[2:]
        if not keys:
            help()
            return 1
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
            print("print help for refresh") #TODO
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
                        return 1 
                    accounts.append(DOAccount(api_key=k[0], ssh_key=ssh_key))
                provision(accounts)
    elif command == "purge":
        purge()
    elif command == "shutdown":
        shutdown()
    else:
        help()

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
        if cursor.fetchall():
            continue
        else:
            cursor.execute("""
                INSERT INTO droplets(key_id, id, ipv4, date, ttl) VALUES((SELECT key_id FROM keys WHERE key=?),?,?,?, ?)""", (account.api_key, d["id"], d["ipv4"], d["date"], account.ttl))
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

def provision(accounts):
    for a in accounts:
       a.create_ssh_key()
       apply_terraform(a) 
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
    output = subprocess.run(["terraform", "init"])
    output = subprocess.run(["terraform", "workspace", "new", account.api_key])
    output = subprocess.run(["terraform", "workspace", "select", account.api_key])
    output = subprocess.run(["terraform", "apply", "-auto-approve", "-var=do_api_token=" + account.api_key, "-var=do_ssh_key=" + account.ssh_key_fingerprint])
    output = subprocess.run(["terraform", "output"], encoding='utf-8', stdout=subprocess.PIPE)
    ttl = output.stdout.split('\n')[0].split(" ")[2]
    account.ttl = math.floor(float(ttl))
    os.chdir(cwd)

def build_inventory(accounts):
    with open("ansible/inventory", "a+") as inventory:
        inventory.seek(0)
        hosts = [line.strip().split(" ")[0] for line in inventory.readlines()]
        if (hosts == []) or (hosts[0] != '[compute]'):
            inventory.write("[compute]\n")
        for a in accounts:
            for d in a.get_active_droplets():
                if d["ipv4"] not in hosts:
                    inventory.write(d["ipv4"] + " api_key=" + a.api_key + " ttl=" + str(a.ttl) + "\n" )

def apply_ansible():
    cwd = os.getcwd()
    os.chdir("ansible/")
    output = subprocess.run(["ansible-playbook", "-i", "inventory", "site.yml"])
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
        printGreen("email: {}  status: {}  ratelimit: {} balance: {}\n".format(status[0], status[1], status[2], balance))
        printPurple(i[0] + "\n")
        for d in cursor.fetchall():
            time_left = math.floor((math.floor(float(d[3])) + int(d[4]) * 3600) - time.time()) / 3600
            pad = (16 - len(str(d[2]))) * " "
            printCyan("    id=")
            print(d[1], end="")
            printCyan("    ipv4=")
            print(d[2].ljust(16, " "), end="")
            print("     with\033[96m {}\033[00m hours left.".format(int(time_left)))
        print()

def purge():
    printGreen("Looking for expired resources...\n")
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
        elif not int(d[0]) in active_droplets:
            cursor.execute("""
                SELECT key FROM keys WHERE key_id=?""",(d[4],))
            key =  cursor.fetchone()
            try:
                if DOAccount(api_key=key[0]).get_droplet(d[0])["id"] == "not_found":
                    unreachable.append((d[0], d[1]))
            except KeyError as e:
                continue
             
    if expired != []:
        printRed("Purging these expired droplets:\n")
        for e in expired:
            print("\t{}, {}".format(e[0], e[1]))
    if unreachable != []:
        printRed("Purging these unreachable droplets:\n")
        for u in unreachable:
            print("\t{}, {}".format(u[0], u[1]))
    if accounts != []:
        printRed("Purging these empty accounts:\n")
        for a in accounts:
            print("\t{}".format(a))
    if not (expired == unreachable == accounts == []):
        printGreen("Does this look correct?")
        printGreen("\n (Only 'yes' will be accepted as confirmation): ")
        answer = input("")
        if answer == "yes":
            for e in expired:
                cursor.execute("""
                    DELETE FROM droplets WHERE id=?""", (e[0],))
            for u in unreachable:
                cursor.execute("""
                    DELETE FROM droplets WHERE id=?""", (u[0],))
            for a in accounts:
                cursor.execute("""
                    DELETE FROM keys WHERE key=?""", (a,))
                output = subprocess.run(["terraform", "workspace", "delete", a])
            printGreen("Done purging.\n")
    else:
        printRed("Nothing found to purge.\n")
    db.commit()

def shutdown():
    printRed("Destroy all droplets for all keys???\n")
    printRed("(Only 'yes' will be accepted as confirmation): ")
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
                status_code = int(r.status_code)
                if status_code == 204:
                    printRed("Account shutdown: ", k[0])

class DOAccount:

    def __init__(self, api_key, ssh_key="", ttl=1):
        self.api_endpoint="https://api.digitalocean.com/v2/"
        self.api_key = api_key
        self.ssh_key = ssh_key
        if ssh_key != "":
            self.ssh_key_fingerprint = self.md5_fingerprint(ssh_key)
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
        r = requests.post(self.api_endpoint + "account/keys", headers=self.api_headers, data=json.dumps({ "name":"key","public_key": self.ssh_key}))
        try:
            fingerprint = str(json.loads(r.text)['ssh_key']['fingerprint'])
            print("ssh fingerprint: ", fingerprint)
        except:
            print("ssh key already exists!")

    def get_droplet(self, id):
        r = requests.get(self.api_endpoint + "droplets/" + str(id), headers=self.api_headers)
        return json.loads(r.text)

    def get_ip(self, id):
        network = self.get_droplet(id)['droplet']['networks']['v4']
        for i,_ in enumerate(network):
            if str(network[i]['type']) == 'public':
                return str(network[i]['ip_address'])

    #return [email, status, ratelimit]
    def get_status(self):
        r = requests.get(self.api_endpoint + "account/", headers=self.api_headers)
        body = json.loads(r.text)["account"]
        return [body["email"], body["status"], r.headers["Ratelimit-Remaining"]]

    def get_balance(self):
        r = requests.get(self.api_endpoint + "customers/my/balance", headers=self.api_headers)
        body = json.loads(r.text)
        return abs(float(body["month_to_date_balance"]))

    #return {"id": id, "ipv4": 0.0.0.0, "date": unix_time}
    def get_active_droplets(self):
        r = requests.get(self.api_endpoint + "droplets", headers=self.api_headers)
        droplets = []
        for d in json.loads(r.text)['droplets']:
            date =  str(int(datetime.datetime.strptime(str(d['created_at']), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()))
            droplets.append({"id": d['id'], "ipv4": self.get_ip(d['id']), "date": date})
        return droplets

if __name__ == "__main__":
    d = DOAccount(api_key="55018d84fa5015c411534c95d0061919a66364b8104c9b71bd5b0ea0989682e8", ssh_key=open("config/id_rsa.pub","r").read())
    e = DOAccount(api_key="391afd0631a0d9fa2ca2ee2b47db1f3114d421b750f60244a07c11f07167dadf", ssh_key=open("config/id_rsa.pub","r").read())
    main()
