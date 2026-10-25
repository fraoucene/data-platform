#!/usr/bin/env bash
# Regénère le livrable S1 : partitions du bucket raw (avec le count de chaque manifest) et graphe des invocations.
# Lecture seule sur AWS. Le numéro de compte est masqué avant toute écriture (le dépôt est public).
#   bash docs/livrables/s1/generer.sh            (profil data-platform par défaut)
set -euo pipefail

cd "$(dirname "$0")"
PROFILE="${PROFILE:-data-platform}"
BUCKET="$(terraform -chdir=../../../infra output -json bucket_names | jq -er .raw)"
mask() { sed -E 's/[0-9]{12}/<account_id>/g'; }

{
  echo "# Partitions de s3://$BUCKET/bodacc/ (généré le $(date -u +%Y-%m-%dT%H:%M:%SZ))"
  echo "# date        count   gz_bytes  fetched_at"
  aws s3 ls "s3://$BUCKET/bodacc/" --profile "$PROFILE" | awk '{print $2}' | sed -n 's|^date=\(.*\)/$|\1|p' |
    while read -r day; do
      aws s3 cp "s3://$BUCKET/bodacc/date=$day/_MANIFEST.json" - --profile "$PROFILE" 2>/dev/null |
        jq -r --arg d "$day" '"\($d)  \(.count)  \(.gz_bytes)  \(.fetched_at)"' ||
        echo "$day  (pas de manifest : partition incomplète)"
    done | column -t
} | mask > partitions-raw.txt

aws cloudwatch get-metric-widget-image --metric-widget file://invocations.json --profile "$PROFILE" \
  --output text --query MetricWidgetImage | base64 --decode > invocations.png

echo "partitions-raw.txt : $(grep -vc '^#' partitions-raw.txt) partitions ; invocations.png : $(wc -c < invocations.png) octets"
