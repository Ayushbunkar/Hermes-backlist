import { NextResponse } from 'next/server';
import pool from '@/lib/db';

export async function GET() {
  try {
    const client = await pool.connect();
    const result = await client.query('SELECT * FROM system_settings WHERE id = 1');
    client.release();
    
    if (result.rows.length === 0) {
      return NextResponse.json({ error: 'Settings not initialized' }, { status: 404 });
    }
    
    const row = result.rows[0];
    return NextResponse.json({
      min_score: row.min_score,
      platforms: JSON.parse(row.platforms || '[]'),
      reminder_intervals_hours: JSON.parse(row.reminder_intervals_hours || '{}'),
      ai_model: row.ai_model,
      schedule_frequency_minutes: row.schedule_frequency_minutes,
      telegram_formatting: row.telegram_formatting,
      business_thresholds: JSON.parse(row.business_thresholds || '{}'),
      learning_enabled: Boolean(row.learning_enabled)
    });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const client = await pool.connect();
    
    // In a real app we'd validate the body schema here
    const updateQuery = 
      UPDATE system_settings SET
        min_score = ,
        platforms = ,
        reminder_intervals_hours = ,
        ai_model = ,
        schedule_frequency_minutes = ,
        telegram_formatting = ,
        business_thresholds = ,
        learning_enabled = 
      WHERE id = 1
    ;
    
    await client.query(updateQuery, [
      body.min_score,
      JSON.stringify(body.platforms),
      JSON.stringify(body.reminder_intervals_hours),
      body.ai_model,
      body.schedule_frequency_minutes,
      body.telegram_formatting,
      JSON.stringify(body.business_thresholds),
      body.learning_enabled ? 1 : 0
    ]);
    
    client.release();
    return NextResponse.json({ success: true });
  } catch (err: any) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
