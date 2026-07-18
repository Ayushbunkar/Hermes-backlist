// @ts-ignore
import { Pool } from 'pg';

import fs from 'fs';
import path from 'path';

let dbUrl = process.env.DATABASE_URL;

if (!dbUrl) {
  try {
    const envPath = path.resolve(process.cwd(), '.env.local');
    const envFile = fs.readFileSync(envPath, 'utf8');
    const match = envFile.match(/^DATABASE_URL=(.*)$/m);
    if (match) {
      dbUrl = match[1].trim();
    }
  } catch (e) {
    // Ignore fs errors
  }
}

const pool = new Pool({
  connectionString: dbUrl,
});

export default pool;
