import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limit = parseInt(searchParams.get('limit') || '50');
  const offset = parseInt(searchParams.get('offset') || '0');
  
  try {
    const client = await pool.connect();
    const result = await client.query(
      'SELECT * FROM notifications ORDER BY created_at DESC LIMIT  OFFSET ',
      [limit, offset]
    );
    client.release();
    return NextResponse.json({ notifications: result.rows });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    if (body.action === 'mark_read' && body.id) {
      const client = await pool.connect();
      await client.query('UPDATE notifications SET is_read = 1 WHERE id = ', [body.id]);
      client.release();
      return NextResponse.json({ success: true });
    }
    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
