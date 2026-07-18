// @ts-ignore
import { Pool } from 'pg';

import fs from 'fs';
import path from 'path';

let dbUrl = process.env.DATABASE_URL;

if (!dbUrl) {
  const possiblePaths = [
    path.resolve(process.cwd(), '.env.local'),
    path.resolve(process.cwd(), 'workspace-dashboard', '.env.local'),
    path.resolve(process.cwd(), '.env'),
    path.resolve(process.cwd(), '../.env.local'),
    path.resolve(process.cwd(), '../.env')
  ];

  for (const p of possiblePaths) {
    try {
      if (fs.existsSync(p)) {
        const envFile = fs.readFileSync(p, 'utf8');
        const match = envFile.match(/^DATABASE_URL=(.*)$/m);
        if (match) {
          dbUrl = match[1].trim().replace(/['"]/g, '');
          console.log(`[DB] Found DATABASE_URL in ${p}`);
          break;
        }
      }
    } catch (e) {
      // Ignore
    }
  }
}

if (!dbUrl) {
  console.error("[DB] CRITICAL ERROR: DATABASE_URL is still undefined after aggressive scanning!");
} else {
  console.log(`[DB] Connection string begins with: ${dbUrl.substring(0, 20)}...`);
}

const pool = new Pool({
  connectionString: dbUrl,
});

export default pool;
