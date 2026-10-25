# Planification des Lambdas par EventBridge Scheduler (et non par une règle EventBridge classique :
# celle-ci ne connaît que l'UTC, Scheduler suit Europe/Paris et l'heure d'été).
# Une entrée de local.schedules = une Lambda déclenchée ; sa clé est celle de local.lambdas.

locals {
  schedules = {
    ingest-bodacc = {
      # cron AWS : minutes heures jour-du-mois mois jour-de-la-semaine année ; un des deux « jour » vaut `?`.
      expression = "cron(0 6 * * ? *)"
      timezone   = "Europe/Paris"
      # Pas de date : la Lambda prend la veille à Paris (resolve_day). Un déclenchement en retard
      # ou réessayé vise donc toujours le bon jour.
      input = "{}"
    }
  }
}

# ---------------------------------------------------------------------------
# Rôle endossé par Scheduler pour invoquer la cible : un par planification.
# ---------------------------------------------------------------------------

# Confiance limitée au compte : sans aws:SourceAccount, une planification d'un autre compte
# pourrait faire endosser ce rôle par Scheduler (« confused deputy »).
data "aws_iam_policy_document" "scheduler_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  for_each = local.schedules

  name               = "${local.prefix}-${each.key}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.scheduler_assume.json
}

# Invoquer cette fonction-là, rien d'autre. Les deux ARN : la fonction, et la fonction qualifiée
# (`:version` ou `:alias`), au cas où la cible deviendrait un alias.
data "aws_iam_policy_document" "scheduler_invoke" {
  for_each = local.schedules

  statement {
    sid     = "InvokeTarget"
    actions = ["lambda:InvokeFunction"]
    resources = [
      module.lambda[each.key].function_arn,
      "${module.lambda[each.key].function_arn}:*",
    ]
  }
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  for_each = local.schedules

  name   = "invoke"
  role   = aws_iam_role.scheduler[each.key].id
  policy = data.aws_iam_policy_document.scheduler_invoke[each.key].json
}

# ---------------------------------------------------------------------------
# La planification elle-même.
# ---------------------------------------------------------------------------

resource "aws_scheduler_schedule" "this" {
  for_each = local.schedules

  name                         = "${local.prefix}-${each.key}"
  description                  = "Déclenche ${module.lambda[each.key].function_name} (${each.value.expression}, ${each.value.timezone})."
  schedule_expression          = each.value.expression
  schedule_expression_timezone = each.value.timezone
  state                        = "ENABLED"

  # OFF : déclenchement à l'heure exacte. Une fenêtre flexible (« dans les 15 min ») sert à lisser
  # beaucoup de planifications à la même heure ; inutile pour une seule.
  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = module.lambda[each.key].function_arn
    role_arn = aws_iam_role.scheduler[each.key].arn
    input    = each.value.input
  }
}
