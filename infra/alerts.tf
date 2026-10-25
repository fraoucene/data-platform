data "aws_caller_identity" "current" {}

resource "aws_sns_topic" "budget_alerts" {
  name = "data-platform-budget-alerts"
}

resource "aws_sns_topic_subscription" "budget_alerts_email" {
  topic_arn = aws_sns_topic.budget_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

data "aws_iam_policy_document" "budget_alerts_topic" {
  statement {
    sid    = "AllowBudgetsPublish"
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }

    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.budget_alerts.arn]

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_sns_topic_policy" "budget_alerts" {
  arn    = aws_sns_topic.budget_alerts.arn
  policy = data.aws_iam_policy_document.budget_alerts_topic.json
}

# ---------------------------------------------------------------------------
# Alertes d'exploitation : un topic par environnement (celui du budget, ci-dessus, est global au compte).
# ---------------------------------------------------------------------------

resource "aws_sns_topic" "alerts" {
  name = "${local.prefix}-alerts"
}

# Reste « PendingConfirmation » tant que le lien du mail reçu après l'apply n'est pas cliqué :
# d'ici là, aucune alarme n'arrive.
resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch publie au nom du service : autorisé pour les alarmes de ce compte seulement.
data "aws_iam_policy_document" "alerts_topic" {
  statement {
    sid       = "AllowCloudWatchAlarms"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.alerts.arn]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_sns_topic_policy" "alerts" {
  arn    = aws_sns_topic.alerts.arn
  policy = data.aws_iam_policy_document.alerts_topic.json
}

# Une alarme par Lambda : au moins une minute avec une invocation en échec (exception non attrapée, timeout)
# parmi les 15 dernières. 15 min couvrent l'essai et les 2 retries asynchrones (~3 min) : une panne = un mail
# ALARM, puis un mail OK 15 min après la dernière erreur.
# Périodes d'1 min, pas une seule période de 15 min : `Errors` n'a de points que quand la fonction tourne.
# Avec 1 période de 900 s, le dernier vrai point (l'erreur) restait dans la plage d'évaluation et l'alarme
# restait en ALARM (mesuré en S1-08) ; avec 15 périodes et 1 seul vrai point, CloudWatch complète les
# minutes vides par `notBreaching` et repasse en OK dès que l'erreur sort de la fenêtre.
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = local.lambdas

  alarm_name        = "${local.prefix}-${each.key}-errors"
  alarm_description = "${module.lambda[each.key].function_name} a échoué : lire `aws logs tail ${module.lambda[each.key].log_group} --since 1h`, puis rejouer avec `make replay`."

  namespace   = "AWS/Lambda"
  metric_name = "Errors"
  dimensions = {
    FunctionName = module.lambda[each.key].function_name
  }

  statistic           = "Sum"
  period              = 60
  evaluation_periods  = 15
  datapoints_to_alarm = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.alerts.arn]
  ok_actions    = [aws_sns_topic.alerts.arn]
}
