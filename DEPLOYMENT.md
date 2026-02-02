# Deployment & Git Workflow

## Git Workflow

### 1. Status Check
Check changed files:
```bash
git status
```

### 2. Stage Changes
Stage all changes:
```bash
git add .
```

### 3. Commit
Commit with a message:
```bash
git commit -m "Your commit message"
```

### 4. Push Changes
To push the current branch to origin:
```bash
git push
```

If it's a new branch:
```bash
git push --set-upstream origin <branch-name>
```

---

## Google Cloud Deployment

### Prerequisites
- Google Cloud CLI installed and authenticated
- Project ID: `retirement-planner-backend-01`
- Region: `us-central1`

### 1. Enable APIs (First Time Only)
```bash
gcloud services enable cloudbuild.googleapis.com run.googleapis.com
```

### 2. Deploy to Cloud Run
Deploy the application from the current directory:
```bash
gcloud run deploy retirement-planner-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

### 3. Verify Deployment
Data will be output after deployment, including the service URL.
Health check:
```bash
curl <SERVICE_URL>/health
```
