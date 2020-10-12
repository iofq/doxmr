# doxmr
`sudo make`

TODO:
daemon/container constantly checking for expiring droplets and terraform destroy them
xmrig proxy
computes run over vpn
monitoring
cpu limit

workflow:
  create new account, verify, and get api key
  run add.py "key"
    add.py verifies key is valid length X
    add key to list of keys 
    adds ssh-key to account X
    run terraform on api key X
      => ip addr
      => droplet id (for daemon parsing actions)
    rebuild ansible inventory with new IP
    run ansible on inventory
  update daemon with new json
