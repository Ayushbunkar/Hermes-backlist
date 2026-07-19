import { NextResponse } from 'next/server';
import pool from '@/lib/db';
import { getSession } from '@/lib/auth';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import os from 'os';

const execAsync = promisify(exec);

export async function DELETE(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { id } = await params;
  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    // Get the project URL before deleting (needed to delete from SQLite too)
    const projResult = await client.query('SELECT project_url FROM projects WHERE id = $1', [id]);
    const projectUrl = projResult.rows[0]?.project_url;

    if (!projectUrl) {
      await client.query('ROLLBACK');
      return NextResponse.json({ error: 'Project not found' }, { status: 404 });
    }

    // Delete related whitelist sites from PostgreSQL
    await client.query('DELETE FROM whitelist_sites WHERE project_id = $1', [id]);

    // Delete the project from PostgreSQL
    await client.query('DELETE FROM projects WHERE id = $1', [id]);

    // Delete related opportunities if they exist based on URL
    await client.query('DELETE FROM opportunities WHERE project_url = $1', [projectUrl]);

    await client.query('COMMIT');

    // Also delete from SQLite (the daemon's source of truth) so it doesn't re-add the project
    const sqliteDbPath = path.join(os.homedir(), '.openclaw-backlink', 'data', 'backlink.db');
    const orchestratorPath = path.join(process.cwd(), '..', 'workspace-bl-orchestrator', 'skills', 'pipeline');
    
    try {
      await execAsync(
        `python -c "import sys; sys.path.insert(0, '${orchestratorPath.replace(/\\/g, '\\\\')}'); import whitelist_db; whitelist_db.delete_project('${projectUrl}', db_path='${sqliteDbPath.replace(/\\/g, '\\\\')}')"`
      );
    } catch (sqliteErr: any) {
      // Log but don't fail - PostgreSQL delete was successful
      console.warn('[DELETE project] SQLite delete warning:', sqliteErr.message);
    }

    return NextResponse.json({ message: 'Project deleted successfully' });
  } catch (err: any) {
    await client.query('ROLLBACK');
    return NextResponse.json({ error: err.message }, { status: 500 });
  } finally {
    client.release();
  }
}
