variable "do_api_token" {
  default = ""
}

provider "digitalocean" {
  token = var.do_api_token
}

resource "digitalocean_droplet" "web" {
  image = "debian-10-x64"
  name  = "doxmr1"
  region = "sfo3"
  size = "s-4vcpu-8gb"
  user_data = "file('user-data.yml')"
}

