# doxmr
a tool for farming large amounts of (free) DigitalOcean accounts using terraform and ansible. Auto-destroys resources before free credit runs out. 

## Requirements:
  - `docker`
  - being a cheap asshole willing to take advantage of a fantastic cloud provider

If you're insane and want to run this outside of the container, you'll need:
  - `terraform >= 0.13`
  - `ansible >= 2.7`
  - `python3.*`
  -  python `requests` module (`pip install requests`)

## Workflow:
Note: this is initially setup for accounts with $100 free credit. If you have a different amount than that, change the calculation in do.tf accordingly.

Edit `ansible/site.yml` to reflect your use case.

(Optional \*) Edit `terraform/do.tf` if you'd like to make changes to the default config (2x 2Vcpu droplets in SFO2).

Create and verify DigitalOcean accounts using one of many [partner links](https://do.co/lnl).

Login to the account and create an API key.

Finally, `./doxmr add <api_key>` to apply terraform and ansible on the account. 

If you ever wish to update ansible config on an account's droplets you can use `./doxmr refresh`


\*WARNING: Changing terraform config, droplet count or size while an account is active could result in charges. This is because it is impossible to get an accurate account balance on timeframes shorter than monthly with the DigitalOcean API. The best we can do is pessimistically calculate when to destroy a node based on its hourly cost and the time since the account was created. Changed terraform variables will not be accounted for in this calculation. So be careful; it's safest to shutdown and prune all non-fresh accounts before making any changes to terraform.

## TODO:
```
took at optimizaions, running terraform in parallel, ls can be faster?
Test everything, esp. pruning optimizations

Features:
separate ansible/terraform configs?
```
