#!/bin/bash

# ===========================================
# GIT HISTORY CLEANUP SCRIPT
# ===========================================
# This script removes sensitive data from git history
# WARNING: This rewrites git history - ensure team coordination

echo "🚨 Starting Git History Cleanup..."
echo "⚠️  This will rewrite git history - ensure you have backups!"

# Check if we're in a git repository
if ! git rev-parse --git-head > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

echo "📋 Current git status:"
git status

echo ""
echo "🔧 Step 1: Removing sensitive files from history..."
echo "Files to remove: .env firebase-service-account.json"

# Remove sensitive files from history
# Note: This requires BFG Repo Cleaner to be installed
# Download from: https://rtyley.github.io/bfg-repo-cleaner/

if command -v java &> /dev/null; then
    if [ -f "bfg.jar" ]; then
        echo "🔄 Running BFG to remove files..."
        java -jar bfg.jar --delete-files .env firebase-service-account.json
        
        echo "🔄 Running BFG to replace sensitive strings..."
        # java -jar bfg.jar --replace-text passwords-to-replace.txt  # File deleted for security
        
        echo "🧹 Cleaning up git refs..."
        git reflog expire --expire=now --all
        git gc --prune=now --aggressive
        
        echo ""
        echo "✅ Git history cleanup completed!"
        echo ""
        echo "⚠️  IMPORTANT: You must force push to update remote:"
        echo "   git push origin --force --all"
        echo ""
        echo "📊 Repository size reduction:"
        du -sh .git
        
    else
        echo "❌ BFG JAR not found. Please download from:"
        echo "   https://rtyley.github.io/bfg-repo-cleaner/"
        echo "   Save as 'bfg.jar' in this directory"
        exit 1
    fi
else
    echo "❌ Java not found. Please install Java to run BFG"
    exit 1
fi

echo ""
echo "🎯 Alternative: Using git filter-branch (slower but built-in)"
echo "If BFG doesn't work, you can use:"
echo "git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch .env firebase-service-account.json' --prune-empty --tag-name-filter cat -- --all"
echo ""
echo "📝 Manual verification steps:"
echo "1. Check history: git log --oneline | grep -E '(\.env|firebase)'"
echo "2. Search for secrets: git grep -i 'password\\|key\\|secret' \$(git rev-list --all)"
echo ""
echo "🔒 After cleanup:"
echo "1. Force push: git push origin --force --all"
echo "2. Notify team to re-clone repository"
echo "3. Update all remote references"
echo "4. Rotate all compromised credentials"
