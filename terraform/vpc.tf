resource "google_compute_network" "vpc" {
  name                    = "photoai-vpc"
  auto_create_subnetworks = true

  depends_on = [google_project_service.apis["compute.googleapis.com"]]
}

resource "google_compute_global_address" "private_ip" {
  name          = "photoai-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_vpc" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]
}

resource "google_vpc_access_connector" "connector" {
  name          = "photoai-connector"
  region        = var.region
  network       = google_compute_network.vpc.name
  ip_cidr_range = "10.8.0.0/28"

  depends_on = [google_project_service.apis["vpcaccess.googleapis.com"]]
}
