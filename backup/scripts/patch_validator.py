import sys
with open('/data/data/com.termux/files/home/.hermes/scripts/evomap_validator.sh', 'r') as f:
    content = f.read()

old = 'log "Claim response status: $CLAIM_STATUS"\n\nif echo "$CLAIM_STATUS" | grep -qE "claimed|success|accepted"; then'

new = '''ALREADY_JOINED=$(echo "$CLAIM_RESP" | python3 -c "
import sys,json; d=json.load(sys.stdin); print('true' if d.get('already_joined') else 'false')
" 2>/dev/null)

log "Claim response status: $CLAIM_STATUS (already_joined=$ALREADY_JOINED)"
if echo "$CLAIM_STATUS" | grep -qE "claimed|success|accepted" || [ "$ALREADY_JOINED" = "true" ]; then'''

if old in content:
    content = content.replace(old, new)
    with open('/data/data/com.termux/files/home/.hermes/scripts/evomap_validator.sh', 'w') as f:
        f.write(content)
    print('Patched successfully')
else:
    print('Pattern not found')
    idx = content.find('Claim response status')
    print(repr(content[idx:idx+400]))
