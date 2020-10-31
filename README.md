# doxmr
`sudo make`

# TODO:
```
ansible only runs on new account/selected accounts (dynamic inventory)
TEST destroy workflow
emergency shutdown all nodes
computes run over vpn (openvpn)
cpu limiting
xmrig proxy
make sure we are handling locked accounts, api failures
dope README with instructions
copy/generate ssh key in Makefile

workflow:
  `doxmr` is just a shell wrapper for docker exec commands to doxmr.py
  sudo make:
    create the management container on system with correct mounts (./config:/config)
  doxmr add:
    provision and store account
  doxmr ls {accounts, nodes}:
    show list of accounts/nodes from sql database
  doxmr refresh:
    take list of keys (or -a), run terraform against them and ansible against the resulting droplets
    used for changing terraform/ansible config
  doxmr purge:
    parse database for droplets/accounts expired and remove them
```
