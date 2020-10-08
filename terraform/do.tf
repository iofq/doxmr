provider "digitalocean" {
  token = var.do_api_token
}

variable "do_api_token" {
  default = ""
}

variable "compute_count" {
  default = 2
}

resource "digitalocean_tag" "compute" {
  name = "doxmr"
}

resource "digitalocean_droplet" "compute" {
  count = var.compute_count
  name = "compute${count.index}"
  image = "debian-10-x64"
  region = "sfo3"
  size = "s-4vcpu-8gb"
  ssh_keys = ["2c:47:58:6e:26:fd:94:c5:a3:62:89:49:72:ef:a3:50"]
  tags = [digitalocean_tag.compute.name]
}

output "compute_ip_addr" {
  value = [digitalocean_droplet.compute.*.ipv4_address]
}

output "compute_id" {
  value = [digitalocean_droplet.compute.*.id]
}
