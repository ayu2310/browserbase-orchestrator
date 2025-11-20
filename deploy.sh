#!/bin/bash
# Quick deployment script for Render

echo "🚀 Browserbase Orchestrator - Render Deployment"
echo "================================================"
echo ""

# Check if git remote exists
if ! git remote get-url origin &>/dev/null; then
    echo "❌ No GitHub remote configured"
    echo ""
    echo "📋 To deploy:"
    echo "1. Create a repository on GitHub"
    echo "2. Run: git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    echo "3. Run: git push -u origin master"
    echo "4. Then go to https://dashboard.render.com → New → Blueprint"
    echo "5. Connect your repo and deploy"
    exit 1
fi

echo "✅ Git remote configured"
echo ""

# Check if pushed
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u} 2>/dev/null || echo "")

if [ -z "$REMOTE" ] || [ "$LOCAL" != "$REMOTE" ]; then
    echo "⚠️  Local changes not pushed to GitHub"
    echo ""
    echo "📤 Pushing to GitHub..."
    git push -u origin master || {
        echo "❌ Failed to push. Please push manually:"
        echo "   git push -u origin master"
        exit 1
    }
    echo "✅ Pushed to GitHub"
else
    echo "✅ Code is up to date on GitHub"
fi

echo ""
echo "================================================"
echo "✅ Ready to deploy on Render!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Go to https://dashboard.render.com"
echo "2. Click 'New +' → 'Blueprint'"
echo "3. Select your repository"
echo "4. Set OPENAI_API_KEY environment variable"
echo "5. Click 'Apply'"
echo ""
echo "Your render.yaml is already configured!"

