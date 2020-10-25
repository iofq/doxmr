provider "digitalocean" {
  token = var.do_api_token
}

variable "do_slugs" {

  default = {
    "s-1vcpu-1gb"  = 0.007440
    "512mb"        = 0.007440
    "s-1vcpu-2gb"  = 0.014880
    "1gb"          = 0.014880
    "s-3vcpu-1gb"  = 0.022320
    "s-2vcpu-2gb"  = 0.022320
    "s-1vcpu-3gb"  = 0.022320
    "s-2vcpu-4gb"  = 0.029760
    "2gb"          = 0.029760
    "s-4vcpu-8gb"  = 0.059520
    "c-2"          = 0.059520
    "4gb"          = 0.059520
    "g-2vcpu-8gb"  = 0.089290
    "gd-2vcpu-8gb" = 0.096730
    "s-6vcpu-16gb" = 0.119050
    "c-4"          = 0.119050
    "8gb"          = 0.119050
    "m-2vcpu-16gb" = 0.133930
  }
}

variable "droplet_count" {
  default = 1
}

variable "droplet_size" {
  default = "s-4vcpu-8gb"
}

variable "do_api_token" {
  default = ""
}

resource "digitalocean_tag" "compute" {
  name = "doxmr"
}

resource "digitalocean_droplet" "compute" {
  count = var.droplet_count
  name = "compute${count.index}"
  image = "debian-10-x64"
  region = "sfo3"
  size = var.droplet_size
  ssh_keys = ["2c:47:58:6e:26:fd:94:c5:a3:62:89:49:72:ef:a3:50"]
  tags = [digitalocean_tag.compute.name]
}

output "ttl" {
  value = 100 / (var.droplet_count * var.do_slugs[var.droplet_size])
}
