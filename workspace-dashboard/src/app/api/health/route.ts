import { NextResponse } from 'next/server';
import pool from '@/lib/db';
import os from 'os';

export async function GET() {
  const healthData = {
    database: { status: 'red', latency: 0 },
    scheduler: { status: 'red', lastHeartbeat: 'never' },
    system: { cpu: 0, memory: 0, uptime: 0 },
    ai: { status: 'yellow', message: 'Mock check' },
    telegram: { status: 'green' }
  };

  try {
    const start = Date.now();
    const client = await pool.connect();
    
    // Check DB
    await client.query('SELECT 1');
    healthData.database.latency = Date.now() - start;
    healthData.database.status = healthData.database.latency < 500 ? 'green' : 'yellow';

    // Check Scheduler Heartbeat
    const res = await client.query('SELECT last_heartbeat FROM system_settings WHERE id = 1');
    if (res.rows.length > 0 && res.rows[0].last_heartbeat) {
      const hb = new Date(res.rows[0].last_heartbeat + 'Z').getTime();
      const diffMinutes = (Date.now() - hb) / 1000 / 60;
      healthData.scheduler.lastHeartbeat = res.rows[0].last_heartbeat;
      if (diffMinutes < 5) healthData.scheduler.status = 'green';
      else if (diffMinutes < 15) healthData.scheduler.status = 'yellow';
      else healthData.scheduler.status = 'red';
    }
    client.release();

    // Check System Metrics
    healthData.system = {
      cpu: os.loadavg()[0],
      memory: 1 - (os.freemem() / os.totalmem()),
      uptime: os.uptime()
    };

    return NextResponse.json(healthData);
  } catch (err: any) {
    return NextResponse.json(healthData, { status: 500 });
  }
}
