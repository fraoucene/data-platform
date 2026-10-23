provider "aws" {
  region  = var.region
  profile = var.profile

  # Garde-fou : refuse de tourner si le profil pointe sur un autre compte.
  allowed_account_ids = [var.account_id]

  default_tags {
    tags = var.tags
  }
}
