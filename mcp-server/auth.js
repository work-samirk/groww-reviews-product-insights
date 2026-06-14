import fs from 'fs';
import path from 'path';
import { google } from 'googleapis';
import http from 'http';

const SCOPES = [
  'https://www.googleapis.com/auth/documents',
  'https://www.googleapis.com/auth/gmail.send',
  'https://www.googleapis.com/auth/gmail.compose'
];

const CREDENTIALS_PATH = path.join(process.cwd(), 'credentials.json');
const TOKEN_PATH = path.join(process.cwd(), 'token.json');

/**
 * Loads or initiates OAuth 2.0 flow to retrieve an authorized Google client.
 */
export async function getOAuth2Client() {
  if (!fs.existsSync(CREDENTIALS_PATH)) {
    throw new Error(`credentials.json not found at ${CREDENTIALS_PATH}. Please provide a desktop OAuth credentials JSON file.`);
  }

  const content = fs.readFileSync(CREDENTIALS_PATH, 'utf8');
  const credentials = JSON.parse(content);
  
  const clientType = credentials.installed ? 'installed' : 'web';
  const { client_secret, client_id, redirect_uris } = credentials[clientType];
  
  // Force local redirect port to 8085 to avoid permission issues on port 80
  const redirectUri = 'http://localhost:8085';
  const oAuth2Client = new google.auth.OAuth2(client_id, client_secret, redirectUri);

  if (fs.existsSync(TOKEN_PATH)) {
    const tokenContent = fs.readFileSync(TOKEN_PATH, 'utf8');
    oAuth2Client.setCredentials(JSON.parse(tokenContent));
    
    // Set up auto-refresh listener
    oAuth2Client.on('tokens', (tokens) => {
      if (tokens.refresh_token) {
        const currentToken = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf8'));
        const updatedToken = { ...currentToken, ...tokens };
        fs.writeFileSync(TOKEN_PATH, JSON.stringify(updatedToken, null, 2));
      }
    });
    
    return oAuth2Client;
  }

  // Token not found, trigger local OAuth server flow
  const authUrl = oAuth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    prompt: 'consent'
  });

  console.error(`\n================================================================`);
  console.error(`[GOOGLE AUTHENTICATION REQUIRED]`);
  console.error(`Please visit this URL in your web browser to authorize access:`);
  console.error(`\n${authUrl}\n`);
  console.error(`================================================================\n`);

  const server = http.createServer();
  const codePromise = new Promise((resolve, reject) => {
    server.on('request', async (req, res) => {
      try {
        const reqUrl = new URL(req.url, 'http://localhost:8085');
        const code = reqUrl.searchParams.get('code');
        if (code) {
          res.writeHead(200, { 'Content-Type': 'text/html' });
          res.end('<h1>Authentication Successful!</h1><p>You can close this tab and return to the terminal.</p>');
          resolve(code);
        } else {
          res.writeHead(400, { 'Content-Type': 'text/html' });
          res.end('<h1>Error</h1><p>Authorization code not found in request.</p>');
        }
      } catch (err) {
        reject(err);
      } finally {
        setTimeout(() => server.close(), 1000);
      }
    });
    
    server.on('error', (err) => {
      reject(new Error(`Failed to start local OAuth redirect server: ${err.message}`));
    });
  });

  // Extract port from redirectUri if possible
  let port = 8085;
  try {
    const parsedUrl = new URL(redirectUri);
    port = parsedUrl.port ? parseInt(parsedUrl.port, 10) : 80;
  } catch (e) {
    // Fallback to 8085
  }

  server.listen(port);
  
  const code = await codePromise;
  const { tokens } = await oAuth2Client.getToken(code);
  oAuth2Client.setCredentials(tokens);
  
  fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens, null, 2));
  console.error("OAuth flow completed successfully. Token stored in token.json");
  
  return oAuth2Client;
}
