import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { google } from 'googleapis';
import { getOAuth2Client } from './auth.js';
import dotenv from 'dotenv';

dotenv.config();

// Initialize the Google client auth variable
let authClient = null;

async function getGoogleAuth() {
  if (!authClient) {
    authClient = await getOAuth2Client();
  }
  return authClient;
}

// Create the MCP server
const server = new Server(
  {
    name: 'groww-workspace-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Define tools
const TOOLS = [
  {
    name: 'append_weekly_report',
    description: 'Appends a weekly review pulse report to the specified Google Doc as a new section with a HEADING_2. If the heading already exists, it returns the link to the existing heading without appending.',
    inputSchema: {
      type: 'object',
      properties: {
        docId: {
          type: 'string',
          description: 'The Google Doc ID where the report will be appended.',
        },
        title: {
          type: 'string',
          description: 'The heading title (e.g., "Groww Review Pulse — Week 24 - 2026").',
        },
        content: {
          type: 'string',
          description: 'The body content of the report to append under the heading.',
        },
      },
      required: ['docId', 'title', 'content'],
    },
  },
  {
    name: 'send_stakeholder_teaser',
    description: 'Sends a brief summary teaser email to stakeholders with a deep link to the appended Google Doc section.',
    inputSchema: {
      type: 'object',
      properties: {
        to: {
          type: 'string',
          description: 'Recipient email address.',
        },
        subject: {
          type: 'string',
          description: 'The subject of the email.',
        },
        bodyHtml: {
          type: 'string',
          description: 'The HTML body of the email (must contain the deep link).',
        },
        bodyText: {
          type: 'string',
          description: 'Plain text version of the email.',
        },
      },
      required: ['to', 'subject', 'bodyHtml', 'bodyText'],
    },
  },
];

// List tools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: TOOLS };
});

// Helper: check if heading exists and return ID
async function findHeadingId(docs, docId, title) {
  const doc = await docs.documents.get({ documentId: docId });
  const body = doc.data.body;
  if (!body || !body.content) return null;

  for (const element of body.content) {
    if (element.paragraph && element.paragraph.paragraphStyle) {
      const style = element.paragraph.paragraphStyle.namedStyleType;
      if (style && style.startsWith('HEADING')) {
        const text = element.paragraph.elements
          .map((el) => (el.textRun ? el.textRun.content : ''))
          .join('')
          .trim();
        if (text.toLowerCase() === title.trim().toLowerCase()) {
          return element.paragraphId;
        }
      }
    }
  }
  return null;
}

// Call tool handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    const auth = await getGoogleAuth();
    const docs = google.docs({ version: 'v1', auth });
    const gmail = google.gmail({ version: 'v1', auth });

    if (name === 'append_weekly_report') {
      const { docId, title, content } = args;
      let targetDocId = docId;

      // Auto-create doc if empty or set to placeholder
      if (!targetDocId || targetDocId === 'CREATE' || targetDocId === 'YOUR_GOOGLE_DOC_ID_HERE') {
        console.error("No valid docId provided. Auto-creating a new Google Doc...");
        const newDoc = await docs.documents.create({
          requestBody: {
            title: 'Groww Weekly Review Pulse',
          },
        });
        targetDocId = newDoc.data.documentId;
        console.error(`Successfully created new Google Doc with ID: ${targetDocId}`);
      }

      // 1. Check if heading already exists (idempotency check)
      const existingId = await findHeadingId(docs, targetDocId, title);
      if (existingId) {
        const docLink = `https://docs.google.com/document/d/${targetDocId}/edit#heading=h.${existingId}`;
        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify({
                status: 'skipped',
                message: `Heading "${title}" already exists in the document.`,
                docLink: docLink,
                headingId: existingId,
                docId: targetDocId,
              }),
            },
          ],
        };
      }

      // 2. Heading does not exist, append it. Fetch doc to find ending index
      const doc = await docs.documents.get({ documentId: targetDocId });
      const body = doc.data.body;
      const lastElement = body.content[body.content.length - 1];
      const length = lastElement.endIndex - 1; // index right before EOF newline

      const textToAppend = `\n\n${title}\n${content}`;

      // Build batch update requests
      const requests = [
        {
          insertText: {
            location: { index: length },
            text: textToAppend,
          },
        },
        {
          updateParagraphStyle: {
            range: {
              startIndex: length + 2, // Skip the two newlines
              endIndex: length + 2 + title.length,
            },
            paragraphStyle: {
              namedStyleType: 'HEADING_2',
            },
            fields: 'namedStyleType',
          },
        },
      ];

      await docs.documents.batchUpdate({
        documentId: targetDocId,
        requestBody: { requests },
      });

      // 3. Find the newly created heading ID
      const newHeadingId = await findHeadingId(docs, targetDocId, title);
      const docLink = `https://docs.google.com/document/d/${targetDocId}/edit#heading=h.${newHeadingId || ''}`;

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'success',
              message: `Appended section "${title}" to document.`,
              docLink: docLink,
              headingId: newHeadingId,
              docId: targetDocId,
            }),
          },
        ],
      };
    } else if (name === 'send_stakeholder_teaser') {
      const { to, subject, bodyHtml, bodyText } = args;

      // Build MIME email
      const boundary = 'groww-pulse-boundary';
      const emailLines = [
        `To: ${to}`,
        `Subject: ${subject}`,
        'MIME-Version: 1.0',
        `Content-Type: multipart/alternative; boundary="${boundary}"`,
        '',
        `--${boundary}`,
        'Content-Type: text/plain; charset=utf-8',
        'Content-Transfer-Encoding: 7bit',
        '',
        bodyText,
        '',
        `--${boundary}`,
        'Content-Type: text/html; charset=utf-8',
        'Content-Transfer-Encoding: 7bit',
        '',
        bodyHtml,
        '',
        `--${boundary}--`,
      ];

      const email = emailLines.join('\n');
      const encodedEmail = Buffer.from(email)
        .toString('base64')
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');

      const response = await gmail.users.messages.send({
        userId: 'me',
        requestBody: {
          raw: encodedEmail,
        },
      });

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify({
              status: 'success',
              messageId: response.data.id,
              threadId: response.data.threadId,
            }),
          },
        ],
      };
    } else {
      throw new Error(`Tool not found: ${name}`);
    }
  } catch (error) {
    return {
      isError: true,
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            status: 'error',
            message: error.message,
            stack: error.stack,
          }),
        },
      ],
    };
  }
});

// Run server using Stdio transport
async function run() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Groww Workspace MCP Server running on stdio');
}

run().catch((error) => {
  console.error('Fatal error running server:', error);
  process.exit(1);
});
