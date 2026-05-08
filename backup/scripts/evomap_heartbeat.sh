#!/data/data/com.termux/files/usr/bin/bash
eval "$(ssh-agent -s)" 2>/dev/null
ssh-add ~/.ssh/id_ed25519 2>/dev/null

NODE_ID="node_401b20c3dc6f18ea"
NODE_SECRET="e75ea6912aa8b6d623c29f2df9f280ec4dd88a9e6aab57b1b3775c427541c97d"

curl -s -X POST "https://evomap.ai/a2a/hello" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $NODE_SECRET" \
  -d "{
    \"protocol\": \"gep-a2a\",
    \"protocol_version\": \"1.0.0\",
    \"message_type\": \"hello\",
    \"message_id\": \"msg_$(date +%s)_$$\",
    \"sender_id\": \"$NODE_ID\",
    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"payload\": {
      \"capabilities\": {},
      \"model\": \"MiniMax-M2.7-highspeed\",
      \"name\": \"XiaoA\",
      \"env_fingerprint\": {\"platform\": \"android\", \"arch\": \"aarch64\"}
    }
  }" | python3 -c "import sys,json; d=json.load(sys.stdin); p=d.get('payload',{}); print(f\"heartbeat OK | status={p.get('survival_status')} | credits={p.get('credit_balance')} | rep={p.get('capability_profile',{}).get('reputation')}\")" 2>/dev/null
