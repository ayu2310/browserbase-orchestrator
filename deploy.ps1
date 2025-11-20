# Quick deployment script for Render (PowerShell)

Write-Host "Browserbase Orchestrator - Render Deployment" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if git remote exists
$remote = git remote get-url origin 2>$null
if (-not $remote) {
    Write-Host "No GitHub remote configured" -ForegroundColor Red
    Write-Host ""
    Write-Host "To deploy:" -ForegroundColor Yellow
    Write-Host "1. Create a repository on GitHub"
    Write-Host "2. Run: git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
    Write-Host "3. Run: git push -u origin master"
    Write-Host "4. Then go to https://dashboard.render.com"
    Write-Host "5. Click New -> Blueprint"
    Write-Host "6. Connect your repo and deploy"
    exit 1
}

Write-Host "Git remote configured: $remote" -ForegroundColor Green
Write-Host ""

# Check if we need to push
Write-Host "Checking if code needs to be pushed..." -ForegroundColor Yellow
$status = git status --porcelain
if ($status) {
    Write-Host "Uncommitted changes detected" -ForegroundColor Yellow
    Write-Host "Committing changes..."
    git add .
    git commit -m "Update for deployment" 2>&1 | Out-Null
}

# Try to push
Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
$pushResult = git push -u origin master 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Push failed or already up to date" -ForegroundColor Yellow
    Write-Host "You may need to push manually: git push -u origin master"
} else {
    Write-Host "Pushed to GitHub" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Ready to deploy on Render!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Go to https://dashboard.render.com"
Write-Host "2. Click New -> Blueprint"
Write-Host "3. Select your repository: $remote"
Write-Host "4. Set OPENAI_API_KEY environment variable"
Write-Host "5. Click Apply"
Write-Host ""
Write-Host "Your render.yaml is already configured!" -ForegroundColor Green
