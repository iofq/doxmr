# doxmr
`sudo make`

TODO:
python script
daemon/container that is constantly checking for expiring droplets and terraform destroys them
xmrig proxy
computes run over vpn
  using api actions


workflow:
  create new account, verify, and get api key
  run add.py "key"
    add.py verifies key is valid length
    adds ssh-key to account
    run terraform on api key
      => ip addr
      => droplet id (for daemon parsing actions)
    rebuild ansible inventory from updated json
    run ansible on inventory
    update daemon
