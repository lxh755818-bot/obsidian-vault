#!/usr/bin/env bash
#===============================================
# Obsidian Vault Git Sync
# 从 Android vault 自动 push 到 GitHub
# 用法: bash obsidian_vault_sync.sh
#===============================================

ANDROID_VAULT="/storage/emulated/0/Documents/xiaoack/小a"
TARGET_BRANCH="master"

cd "$ANDROID_VAULT" || {
    echo "[sync] Vault not found: $ANDROID_VAULT"
    exit 1
}

# 检查是否有变更
if git diff --quiet && git diff --cached --quiet && git diff --quiet HEAD; then
    echo "[sync] No changes, skipping"
    exit 0
fi

# 添加所有变更（忽略 .obsidian 缓存）
git add . \
    ':!.obsidian/workspace-mobile.json' \
    ':!.obsidian/graph.json' \
    ':!.obsidian/.DS_Store' \
    ':!未命名.base'

# 生成 commit
MSG="Auto-sync $(date '+%Y-%m-%d %H:%M')"
git commit -m "$MSG" 2>/dev/null || {
    echo "[sync] Nothing to commit"
    exit 0
}

# 推送到 GitHub（master → main）
echo "[sync] Pushing to origin..."
git push origin "$TARGET_BRANCH":main 2>&1
STATUS=$?

if [ $STATUS -eq 0 ]; then
    echo "[sync] ✅ Pushed successfully"
else
    echo "[sync] ❌ Push failed (check network / token)"
fi

exit $STATUS
