import { NextResponse } from 'next/server';
import pool from '@/lib/db';
import { getSession } from '@/lib/auth';

export async function DELETE(request: Request, { params }: { params: { id: string } }) {
  const session = await getSession();
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { id } = params;

  try {
    const client = await pool.connect();
    
    await client.query('BEGIN');
    
    // Get the project URL before deleting
    const projResult = await client.query('SELECT project_url FROM projects WHERE id = $1', [id]);
    const projectUrl = projResult.rows[0]?.project_url;

    // Delete related whitelist sites
    await client.query('DELETE FROM whitelist_sites WHERE project_id = $1', [id]);
    
    // Delete the project
    await client.query('DELETE FROM projects WHERE id = $1', [id]);

    // Optional: Delete related opportunities if they exist based on URL
    if (projectUrl) {
        await client.query('DELETE FROM opportunities WHERE project_url = $1', [projectUrl]);
    }

    await client.query('COMMIT');
    
    client.release();
    
    return NextResponse.json({ message: 'Project deleted successfully' });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
