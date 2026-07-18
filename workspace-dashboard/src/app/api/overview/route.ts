import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET() {
  try {
    const client = await pool.connect();
    
    // Total
    const totalResult = await client.query('SELECT COUNT(*) FROM opportunities');
    const total = parseInt(totalResult.rows[0].count);

    // Grouped by status
    const statusResult = await client.query('SELECT status, COUNT(*) FROM opportunities GROUP BY status');
    let approved = 0;
    let rejected = 0;
    let pending = 0;
    
    statusResult.rows.forEach(row => {
      if (row.status === 'approved') approved = parseInt(row.count);
      if (row.status === 'rejected') rejected = parseInt(row.count);
      if (row.status === 'pending') pending = parseInt(row.count);
    });

    // Averages
    const avgResult = await client.query('SELECT AVG(score_100) as avg_score, AVG(confidence) as avg_conf FROM opportunities WHERE score_100 IS NOT NULL');
    const averageScore = parseFloat(avgResult.rows[0].avg_score || 0).toFixed(1);
    const averageConfidence = parseFloat(avgResult.rows[0].avg_conf || 0).toFixed(1);

    client.release();

    return NextResponse.json({
      total,
      approved,
      rejected,
      pending,
      averageScore: Number(averageScore),
      averageConfidence: Number(averageConfidence)
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
