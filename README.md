# doxmr

## Requirements:
  - just docker!

If you're insane and want to run this outside of a container, you'll need:
  - `terraform >= 0.13`
  - `ansible >= 2.7`
  - `python3.*`
  - python `requests` module (`pip install requests`)

## Usage:
Edit ansible/roles/compute/tasks/init.yml to run your xmrig container/config file
Edit terraform/do.tf if you'd like to make changes to the default config (2x 4Vcpu droplets in SFO3)
`./doxmr add <api_key>`

## TODO:
```
computes run over vpn (openvpn or just an ssh tunnel maybe?)
is it safe to auto-prune?
TEST destroy workflow (seems solid thus far but it realllllly cant fail)
look at optimizaions, running terraform in parallel, purge and ls can be faster?
cheeky README
```
