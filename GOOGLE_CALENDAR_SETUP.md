# Google Calendar Integration Setup Guide

This guide will help you connect your AI booking assistant to your real Google Calendar.

## Option 1: Service Account (Recommended for Production)

### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Note your project ID

### Step 2: Enable Google Calendar API
1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google Calendar API"
3. Click "Enable"

### Step 3: Create Service Account
1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Enter name: `ai-booking-assistant`
4. Add description: `Service account for AI booking assistant`
5. Click "Create and Continue"
6. Skip role assignment, click "Done"

### Step 4: Generate Credentials File
1. Click on your service account email
2. Go to "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format
5. Click "Create"
6. The `credentials.json` file will download

### Step 5: Install Credentials
1. Place the downloaded file in your project root
2. Rename it to `credentials.json`
3. **Important**: Never commit this file to version control

### Step 6: Share Calendar with Service Account
1. Open Google Calendar
2. Find the service account email in your `credentials.json` file
3. Share your calendar with this email address
4. Give it "Make changes to events" permission

## Option 2: OAuth2 (For Personal Use)

### Step 1-2: Same as above (Create project, enable API)

### Step 3: Create OAuth2 Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure consent screen if prompted
4. Select "Desktop application"
5. Name it `AI Booking Assistant`
6. Click "Create"

### Step 4: Download Client Secrets
1. Download the JSON file
2. Rename it to `client_secrets.json`
3. Place it in your project root

### Step 5: First Run Authentication
1. Start the application
2. A browser window will open for authentication
3. Sign in with your Google account
4. Grant calendar permissions
5. The app will save your token automatically

## Testing the Integration

Once you've set up either option, restart your application:

1. The calendar service will automatically detect your credentials
2. Check the logs for "Google Calendar service initialized successfully"
3. Test booking an appointment through the chat interface
4. Verify the event appears in your Google Calendar

## Troubleshooting

### "No valid Google Calendar credentials found"
- Ensure `credentials.json` (service account) or `client_secrets.json` (OAuth2) is in the project root
- Check file permissions
- Verify the JSON format is valid

### "Access denied" errors
- For service account: Ensure the calendar is shared with the service account email
- For OAuth2: Re-run the authentication flow
- Check API is enabled in Google Cloud Console

### Events not appearing in calendar
- Verify the calendar ID being used
- Check timezone settings
- Ensure proper permissions are granted

## Security Notes

1. **Never commit credential files to version control**
2. Add to `.gitignore`:
   ```
   credentials.json
   client_secrets.json
   token.json
   ```
3. Use environment variables in production
4. Regularly rotate service account keys
5. Use minimum required permissions

## Next Steps

After successful integration:
- The mock calendar service will be automatically replaced
- All booking functionality will work with your real Google Calendar
- Events will be created with proper calendar invitations
- You can view and manage appointments through Google Calendar

Your AI booking assistant is now fully integrated with Google Calendar!