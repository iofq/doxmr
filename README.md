# doxmr
`sudo make`

# TODO:
refresh for python script (rerun terraform, ansible on all keys in file)
store keys, droplet info and creation date locally in json rather than always querying
weigh using terraform vs raw API calls
xmrig proxy to control node
computes run over vpn (openvpn)
cpu limiting/dynamic droplet allocation
monitoring (if destroy service didn't run, email me)

destroy workflow:
  control node has list of api keys
  calculated expiration time based on # of droplets per account and price for droplet
  check json list vs system time
  destroy expiring droplets

container:
  install terraform, ansible, python, pip
  cronjob running destroy checks

workflow:
  `doxmr` is just a shell wrapper for docker exec commands to doxmr.py
  doxmr init:
    create the container on system with correct mounts (./data:/data)
      mounting the keys file and .tfstate files
  doxmr refresh:
    take list of keys, run terraform against them and ansible against the resulting droplets
    used for adding new keys or changing terraform/ansible config
    build new json store
  doxmr destroy:
    parse json for droplets expiring and destroy them
