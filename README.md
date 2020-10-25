# doxmr
`sudo make`

# TODO:
```
destroy workflow:
  each node has its own api keys from ansible template
  calculated ttl based on # of droplets per account and price for droplet DONE
  selfdestruct each node
container:
  install terraform, ansible, python, pip
  use docker modules for ansible instead of shell
computes run over vpn (openvpn)
cpu limiting
xmrig proxy to control node
monitoring (if destroy service didn't run, email me)
make sure we are handling locked accounts, api failures



workflow:
  `doxmr` is just a shell wrapper for docker exec commands to doxmr.py
  doxmr init:
    create the container on system with correct mounts (./data:/data)
      mounting the keys file and .tfstate files
  doxmr add:
    add key to config/keys
    add ssh_key to key via api
    run terraform and ansible
    add to database store
  doxmr refresh:
    take list of keys, run terraform against them and ansible against the resulting droplets
    used for adding new keys in bulk or changing terraform/ansible config
    build new database store
  doxmr destroy:
    parse database for droplets expiring and destroy them
```
