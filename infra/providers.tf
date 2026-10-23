provider "aws" {
  region  = var.region
  profile = var.profile

  # Garde-fou : refuse de tourner si le profil pointe sur un autre compte.
  allowed_account_ids = [var.account_id]

  # Tags posés sur toutes les ressources taggables, root et modules.
  # merge() : var.tags garde sa validation (project obligatoire), on y ajoute
  # les tags calculés par environnement.
  default_tags {
    tags = merge(var.tags, {
      environment = var.environment
      managed_by  = "terraform"
    })
  }
}
