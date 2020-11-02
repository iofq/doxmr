# doxmr

## Requirements:
  - just docker!

If you're insane and want to run this outside of a container, you'll need:
  > `terraform >= 0.13`
  > `ansible >= 2.7`
  > `python3.*`
  > python `requests` module (`pip install requests`)

## Usage:
`./doxmr`

## TODO:
```
computes run over vpn (openvpn or just an ssh tunnel maybe?)
is it safe to auto-prune?
TEST destroy workflow (seems solid thus far but it realllllly cant fail)
look at optimizaions, running terraform in parallel, purge and ls can be faster?
cheeky README
```
