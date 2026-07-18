import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const status = searchParams.get('status') || 'pending';
  const limit = parseInt(searchParams.get('limit') || '50');
  const offset = parseInt(searchParams.get('offset') || '0');

  try {
    const client = await pool.connect();
    
    const query = 
      SELECT id, title, url, platform, category, score_100, confidence, status, business_impact, run_id, created_at, pending_since
      FROM opportunities
      WHERE status = 
      ORDER BY created_at DESC
      LIMIT  OFFSET 
    ;
    const result = await client.query(query, [status, limit, offset]);

    const countQuery = SELECT COUNT(*) FROM opportunities WHERE status = ;
    const countResult = await client.query(countQuery, [status]);

    client.release();

    return NextResponse.json({
      data: result.rows,
      total: parseInt(countResult.rows[0].count),
      page: Math.floor(offset / limit) + 1,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
