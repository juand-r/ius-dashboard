# Authentication System Details

> **Quick Setup**: See main [README.md](README.md) for deployment steps using `./deploy-railway.sh`

## How Authentication Works

The dashboard uses **HTTP Basic Auth** with bcrypt password hashing to protect sensitive datasets like DetectiveQA content due to copyright concerns.

### Architecture:
- **Express proxy server** handles authentication (port 3000 locally, $PORT on Railway)
- **FastAPI backend** serves content (port 8000)  
- **Protected routes** require username/password before accessing content
- **Session persistence** - authenticate once per browser session

## Generate Password Hash

Use the included generator script:
```bash
node generate-password.js
# Follow the prompts to generate a bcrypt hash
```

Or manually:
```bash
node -e "console.log(require('bcryptjs').hashSync('your-password', 10))"
```

## Environment Variables

### Required Variables:
```bash
PROTECTED_CONTENT_USERNAME=researcher           # Username for HTTP Basic Auth
PROTECTED_CONTENT_PASSWORD_HASH=<bcrypt-hash>   # Generated hash from above
PROTECTED_DATASETS=detectiveqa,booookscore      # Comma-separated dataset names
```

### Local Development (.env file):
```
PROTECTED_CONTENT_USERNAME=researcher
PROTECTED_CONTENT_PASSWORD_HASH=$2a$10$your-actual-hash-here
PROTECTED_DATASETS=detectiveqa,booookscore
FASTAPI_PORT=8000
```

## Testing Authentication

1. **Unprotected content**: Visit `http://localhost:3000/bmds` (no auth required)
2. **Protected content**: Visit `http://localhost:3000/detectiveqa` (auth required for data)
3. **Browser will prompt**: Enter username and password when loading protected data
4. **Session persists**: Navigate freely within protected content after authentication

## Adding More Protected Datasets

To protect additional datasets, update the `PROTECTED_DATASETS` environment variable:
```
PROTECTED_DATASETS=detectiveqa,anotherdataset,thirddataset
```

This will protect:
- `/data/outputs/chunks/anotherdataset*`
- `/data/outputs/summaries/anotherdataset*`
- `/api/*anotherdataset*`

## Protected Routes

The following routes require authentication when accessing protected datasets:

- `/data/outputs/chunks/{dataset}*` - Raw chunk data
- `/data/outputs/summaries/{dataset}*` - Summary data  
- `/data/prompts/{dataset}*` - Prompt files
- `/api/*{dataset}*` - API endpoints (except `/api/files`)
- `/{dataset}/` - Dashboard pages for protected datasets

## Security Notes

- **Password hashing**: bcrypt with 10 salt rounds
- **Transport security**: HTTP Basic Auth (secure over HTTPS in production)
- **Session persistence**: Authenticate once per browser session
- **Configurable protection**: Add datasets via `PROTECTED_DATASETS` environment variable
- **Clear authentication**: Close browser or clear site data to logout

## Troubleshooting

### Authentication Not Working on Railway:
1. Check environment variables are set: `railway variables`
2. Redeploy to apply new variables: `railway redeploy`
3. Verify password hash matches your intended password

### Local Authentication Issues:
1. Ensure `.env` file exists in project root
2. Check Express server is running on port 3000 (not 8000 directly)
3. Verify no conflicting environment variables in shell