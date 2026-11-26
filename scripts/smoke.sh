#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:8090}"

echo "== health =="
curl -sf "$API/health"
echo

echo "== login =="
LOGIN=$(curl -sf -X POST "$API/api/auth/login" -H 'Content-Type: application/json' \
  -d '{"email":"owner@flowsuite.com","password":"owner123"}')
TOKEN=$(python3 -c "import sys,json; print(json.loads(sys.argv[1])['access_token'])" "$LOGIN")
ORG=$(curl -sf "$API/api/orgs" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])")
echo "org=$ORG"
AUTH=(-H "Authorization: Bearer $TOKEN" -H "X-Org-Id: $ORG" -H "Content-Type: application/json")

echo "== create customer =="
curl -sf -X POST "$API/api/customers" "${AUTH[@]}" -d '{"name":"Smoke Co","email":"smoke@example.com"}' >/dev/null

echo "== create project + task =="
PID=$(curl -sf -X POST "$API/api/projects" "${AUTH[@]}" -d '{"name":"Smoke Project"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -sf -X POST "$API/api/projects/$PID/tasks" "${AUTH[@]}" -d '{"title":"First task"}' >/dev/null

echo "== billing summary =="
curl -sf "$API/api/billing/summary" -H "Authorization: Bearer $TOKEN" -H "X-Org-Id: $ORG" | python3 -m json.tool | head -30

echo "== stub upgrade pro =="
curl -sf -X POST "$API/api/billing/stub-upgrade" "${AUTH[@]}" -d '{"plan_slug":"pro"}' >/dev/null

echo "== audit =="
curl -sf "$API/api/audit" -H "Authorization: Bearer $TOKEN" -H "X-Org-Id: $ORG" | python3 -c "import sys,json; print('entries', len(json.load(sys.stdin)))"

echo "SMOKE OK"
